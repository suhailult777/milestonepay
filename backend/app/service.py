import json
import sqlite3
import time
import uuid
from datetime import date
from decimal import Decimal

from . import db
from .extraction import ProposedMilestone, ProposedPlan, validate_plan
import httpx
from pydantic import BaseModel

from .paypal import PayPalError, PayPalPort


class Rejected(Exception):
    pass


class PlanMilestoneEdit(BaseModel):
    id: str
    title: str
    amount: str
    due_date: str


class PlanEdit(BaseModel):
    client_name: str
    client_email: str
    total: str
    currency: str = "USD"
    milestones: list[PlanMilestoneEdit]


HANDLED = {"INVOICING.INVOICE.PAID", "INVOICING.INVOICE.REFUNDED", "INVOICING.INVOICE.CANCELLED"}


class Service:
    def __init__(self, conn: sqlite3.Connection, paypal: PayPalPort, merchant_email: str):
        self.c, self.pp, self.merchant = conn, paypal, merchant_email

    # ---------- plan ----------
    def propose(self, plan: ProposedPlan, source_text: str, extraction_source: str) -> dict:
        errors = validate_plan(plan, source_text)
        pid = uuid.uuid4().hex[:12]
        status = "BLOCKED" if errors else "PROPOSED"
        with db.tx(self.c):
            self.c.execute("INSERT INTO projects(id,client_name,client_email,total,currency,source_text,status,extraction_source,created)"
                           " VALUES(?,?,?,?,?,?,?,?,?)",
                           (pid, plan.client_name, plan.client_email, plan.total, plan.currency, source_text,
                            status, extraction_source, time.time()))
            for i, m in enumerate(plan.milestones, 1):
                self.c.execute("INSERT INTO milestones(id,project_id,seq,title,amount,currency,due_date,evidence,status,request_id)"
                               " VALUES(?,?,?,?,?,?,?,?,?,?)",
                               (uuid.uuid4().hex[:12], pid, i, m.title, m.amount, m.currency, m.due_date, m.evidence,
                                "PLANNED", str(uuid.uuid4())))
            db.audit(self.c, pid, f"ai:{extraction_source}", "proposed_plan",
                     {"errors": errors, "ambiguities": plan.ambiguities})
        return {"project_id": pid, "status": status, "errors": errors, "ambiguities": plan.ambiguities}

    def approve(self, pid: str, approver: str) -> None:
        p = self._project(pid)
        if p["status"] != "PROPOSED":
            raise Rejected(f"Plan is {p['status']}; only a valid PROPOSED plan can be approved.")
        with db.tx(self.c):
            self.c.execute("UPDATE projects SET status='APPROVED' WHERE id=?", (pid,))
            db.audit(self.c, pid, f"human:{approver}", "approved_plan", {})

    def update_plan(self, pid: str, edit: PlanEdit, approver: str) -> dict:
        """Human correction before approval. Evidence quotes stay fixed."""
        p = self._project(pid)
        if p["status"] not in ("PROPOSED", "BLOCKED"):
            raise Rejected(f"Plan is {p['status']}; only a proposed or blocked plan can be edited.")
        if not edit.client_name.strip():
            raise Rejected("Client name is required.")
        rows = [dict(r) for r in self.c.execute(
            "SELECT id,title,amount,due_date,evidence FROM milestones WHERE project_id=? ORDER BY seq", (pid,))]
        if [r["id"] for r in rows] != [m.id for m in edit.milestones]:
            raise Rejected("The milestone set changed. Refresh the project and try again.")
        by_id = {r["id"]: r for r in rows}
        proposed = [
            ProposedMilestone(
                title=m.title.strip() or by_id[m.id]["title"],
                amount=m.amount.strip(),
                currency=edit.currency,
                due_date=m.due_date.strip(),
                evidence=by_id[m.id]["evidence"],
            )
            for m in edit.milestones
        ]
        plan = ProposedPlan(
            client_name=edit.client_name.strip(), client_email=edit.client_email.strip(),
            total=edit.total.strip(), currency=edit.currency, milestones=proposed, ambiguities=[],
        )
        errors = validate_plan(plan, p["source_text"])
        status = "BLOCKED" if errors else "PROPOSED"
        with db.tx(self.c):
            self.c.execute("UPDATE projects SET client_name=?, client_email=?, total=?, currency=?, status=? WHERE id=?",
                           (plan.client_name, plan.client_email, plan.total, plan.currency, status, pid))
            for m in edit.milestones:
                self.c.execute("UPDATE milestones SET title=?, amount=?, due_date=? WHERE id=? AND project_id=?",
                               (m.title.strip() or by_id[m.id]["title"], m.amount.strip(), m.due_date.strip(), m.id, pid))
            db.audit(self.c, pid, f"human:{approver}", "edited_plan",
                     {"status": status, "errors": errors, "milestones": len(edit.milestones)})
        return {"project": self.view(pid), "errors": errors}

    # ---------- invoices (two separate human gates) ----------
    def _prior_all_paid(self, m) -> bool:
        r = self.c.execute("SELECT COUNT(*) FROM milestones WHERE project_id=? AND seq<? AND status!='PAID'",
                           (m["project_id"], m["seq"])).fetchone()[0]
        return r == 0

    def draft_invoice(self, mid: str, approver: str) -> dict:
        m = self._milestone(mid)
        p = self._project(m["project_id"])
        if p["status"] != "APPROVED":
            raise Rejected("Approve the plan first.")
        if not self._prior_all_paid(m):
            raise Rejected("Previous milestone is not confirmed PAID by PayPal.")
        if m["invoice_id"]:
            return {"invoice_id": m["invoice_id"], "duplicate": True}
        if m["op_state"] != "NONE":
            raise Rejected(f"Invoice creation is {m['op_state']}; run reconciliation before any retry.")
        # Atomic single-writer claim: only one caller can move NONE -> IN_FLIGHT.
        cur = self.c.execute("UPDATE milestones SET op_state='IN_FLIGHT', op_note=? WHERE id=? AND op_state='NONE'"
                             " AND invoice_id IS NULL", (f"claimed by {approver} at {time.time()}", mid))
        if cur.rowcount != 1:
            raise Rejected("Another invoice creation for this milestone is in progress.")
        number = f"MP-{m['project_id']}-{m['seq']}"
        try:
            iid = self.pp.create_draft_invoice(
                request_id=m["request_id"], merchant_email=self.merchant, recipient_email=p["client_email"],
                title=m["title"], amount=m["amount"], currency=m["currency"], due_date=m["due_date"], number=number)
        except PayPalError as e:
            if e.status < 500 and e.status not in (408, 409, 429):
                # Definite rejection: PayPal did not create the invoice. Safe to release the claim.
                self.c.execute("UPDATE milestones SET op_state='NONE', op_note=? WHERE id=?", (str(e)[:200], mid))
                db.audit(self.c, p["id"], "paypal", "create_rejected", {"milestone": m["seq"], "debug_id": e.debug_id})
                raise Rejected(f"PayPal rejected the invoice: {e}")
            return self._ambiguous(m, p, str(e))
        except (httpx.TransportError, TimeoutError) as e:
            return self._ambiguous(m, p, repr(e))
        with db.tx(self.c):
            self.c.execute("UPDATE milestones SET invoice_id=?, status='DRAFTED', op_state='DONE' WHERE id=?", (iid, mid))
            db.audit(self.c, p["id"], f"human:{approver}", "drafted_invoice",
                     {"milestone": m["seq"], "invoice_id": iid, "paypal_request_id": m["request_id"], "number": number})
        return {"invoice_id": iid, "duplicate": False}

    def _ambiguous(self, m, p, why: str) -> dict:
        with db.tx(self.c):
            self.c.execute("UPDATE milestones SET op_state='RECONCILIATION_REQUIRED', op_note=? WHERE id=?", (why[:200], m["id"]))
            db.audit(self.c, p["id"], "system", "create_outcome_unknown", {"milestone": m["seq"], "error": why[:200]})
        raise Rejected("PayPal outcome unknown (timeout or server error). Automatic retry is blocked; run reconciliation.")

    def reconcile_creation(self, mid: str, approver: str) -> dict:
        """Human-triggered. Covers timeouts and crashes left IN_FLIGHT. Looks up by our unique invoice number."""
        m = self._milestone(mid)
        p = self._project(m["project_id"])
        if m["op_state"] not in ("RECONCILIATION_REQUIRED", "IN_FLIGHT"):
            raise Rejected(f"Nothing to reconcile (state {m['op_state']}).")
        found = self.pp.find_by_number(f"MP-{m['project_id']}-{m['seq']}")
        matched: list[str] = []
        mismatches: list[dict] = []
        for iid in found:
            try:
                inv = self.pp.get_invoice(iid)
            except PayPalError as e:
                mismatches.append({"invoice_id": iid, "reason": f"lookup failed with PayPal {e.status}"})
                continue
            ok, why = self._invoice_matches(m, p, inv)
            if ok:
                matched.append(iid)
            else:
                mismatches.append({"invoice_id": iid, "reason": why})
        if len(matched) == 1:
            with db.tx(self.c):
                self.c.execute("UPDATE milestones SET invoice_id=?, status='DRAFTED', op_state='DONE' WHERE id=?", (matched[0], mid))
                db.audit(self.c, m["project_id"], f"human:{approver}", "reconciled_creation",
                         {"recovered_invoice_id": matched[0]})
            return {"recovered_invoice_id": matched[0]}
        if not found:
            with db.tx(self.c):
                self.c.execute("UPDATE milestones SET op_state='NONE' WHERE id=?", (mid,))
                db.audit(self.c, m["project_id"], f"human:{approver}", "reconciled_creation",
                         {"recovered_invoice_id": None})
            return {"recovered_invoice_id": None, "note": "No invoice exists at PayPal; creation may be retried by a human."}
        result = {
            "error": "Found invoice(s) with this number, but none matched the milestone exactly; resolve manually in PayPal.",
            "ids": found,
            "mismatches": mismatches,
        }
        with db.tx(self.c):
            db.audit(self.c, m["project_id"], f"human:{approver}", "reconciled_creation", result)
        return result

    def _invoice_matches(self, m, p, inv: dict) -> tuple[bool, str]:
        """A recovered invoice is only usable if it matches this milestone exactly."""
        merchant = ((inv.get("invoicer") or {}).get("email_address") or "").lower()
        if merchant != self.merchant.lower():
            return False, "merchant mismatch"
        amount = inv.get("amount") or {}
        if amount.get("currency_code") != m["currency"]:
            return False, "currency mismatch"
        try:
            if Decimal(amount.get("value", "0")) != Decimal(m["amount"]):
                return False, "amount mismatch"
        except Exception:
            return False, "amount unreadable"
        emails = {
            ((r.get("billing_info") or {}).get("email_address") or "").lower()
            for r in (inv.get("primary_recipients") or [])
        }
        if p["client_email"].lower() not in emails:
            return False, "recipient mismatch"
        return True, ""

    def send_invoice(self, mid: str, approver: str, confirm: bool) -> dict:
        m = self._milestone(mid)
        if not confirm:
            raise Rejected("Explicit confirmation required to send.")
        if m["status"] != "DRAFTED":
            raise Rejected(f"Milestone is {m['status']}; only DRAFTED can be sent.")
        if m["hold"] or not self._prior_all_paid(m):
            raise Rejected("On hold: an earlier milestone is no longer confirmed PAID.")
        link = self.pp.send_invoice(m["invoice_id"], f"send-{m['request_id']}")
        with db.tx(self.c):
            self.c.execute("UPDATE milestones SET status='SENT', pay_link=? WHERE id=?", (link, mid))
            db.audit(self.c, m["project_id"], f"human:{approver}", "sent_invoice",
                     {"milestone": m["seq"], "invoice_id": m["invoice_id"]})
        return {"pay_link": link}

    # ---------- webhook ----------
    def handle_webhook(self, headers: dict[str, str], raw: bytes) -> dict:
        if not self.pp.verify_webhook(headers, raw):
            db.audit(self.c, None, "paypal", "webhook_rejected", {"reason": "signature"})
            raise Rejected("Webhook signature verification failed.")
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            raise Rejected("Webhook body is not valid JSON.")
        eid, etype = ev.get("id"), ev.get("event_type")
        if not isinstance(eid, str) or not eid or not isinstance(etype, str) or not etype:
            raise Rejected("Webhook event is missing id or event_type.")
        res = ev.get("resource") or {}
        invoice = res.get("invoice") if isinstance(res.get("invoice"), dict) else {}
        inv_id = invoice.get("id") or res.get("invoice_id")
        try:
            self.c.execute("INSERT INTO webhook_events VALUES(?,?,?,?,?)", (eid, etype, inv_id, "processing", time.time()))
        except sqlite3.IntegrityError:
            prev = self.c.execute("SELECT outcome FROM webhook_events WHERE event_id=?", (eid,)).fetchone()
            if prev["outcome"] != "processing":  # crashed mid-processing -> safe to re-run (reconcile is idempotent)
                return {"outcome": "duplicate_ignored"}
        outcome = self._apply(etype, inv_id)
        self.c.execute("UPDATE webhook_events SET outcome=? WHERE event_id=?", (outcome, eid))
        return {"outcome": outcome}

    def _apply(self, etype: str, inv_id: str | None) -> str:
        if etype not in HANDLED:
            return "ignored_event_type"
        m = self.c.execute("SELECT * FROM milestones WHERE invoice_id=?", (inv_id,)).fetchone()
        if not m:
            return "unknown_invoice"
        if m["status"] not in ("SENT", "PAID", "PARTIAL", "MISMATCH"):
            with db.tx(self.c):
                db.audit(self.c, m["project_id"], "paypal", "webhook_out_of_order", {"status": m["status"], "event": etype})
            return "out_of_order_ignored"
        # Never trust the event body for money: reconcile against PayPal's current invoice.
        inv = self.pp.get_invoice(inv_id)
        st = inv.get("status")
        paid = (inv.get("payments") or {}).get("paid_amount") or {}
        amount = inv.get("amount") or {}
        checks = {
            "merchant": (inv.get("invoicer") or {}).get("email_address", "").lower() == self.merchant.lower(),
            "currency": amount.get("currency_code") == m["currency"] == paid.get("currency_code"),
            "amount": Decimal(amount.get("value", "0")) == Decimal(m["amount"]),
            "paid_full": Decimal(paid.get("value", "0")) == Decimal(m["amount"]),
        }
        if st in ("REFUNDED", "PARTIALLY_REFUNDED", "CANCELLED"):
            new = "REFUNDED" if "REFUND" in st else "CANCELLED"
        elif st == "PARTIALLY_PAID":
            new = "PARTIAL"
        elif st == "PAID" and all(checks.values()):
            new = "PAID"
        elif st == "PAID":
            new = "MISMATCH"
        else:
            new = m["status"]
        old = m["status"]
        with db.tx(self.c):
            self.c.execute("UPDATE milestones SET status=?, paid_amount=? WHERE id=?", (new, paid.get("value"), m["id"]))
            if old == "PAID" and new != "PAID":
                # Money reversed after we unlocked later milestones: hold every later one.
                self.c.execute("UPDATE milestones SET hold=? WHERE project_id=? AND seq>?",
                               (f"milestone {m['seq']} became {new}", m["project_id"], m["seq"]))
                db.audit(self.c, m["project_id"], "system", "downstream_hold", {"from_milestone": m["seq"], "reason": new})
            elif new == "PAID":
                self.c.execute("UPDATE milestones SET hold=NULL WHERE project_id=? AND seq>?", (m["project_id"], m["seq"]))
            db.audit(self.c, m["project_id"], "paypal", "reconciled",
                     {"milestone": m["seq"], "paypal_status": st, "checks": checks, "result": new})
        return f"milestone_{new.lower()}"

    def refresh_from_paypal(self, mid: str, approver: str) -> dict:
        """Poll PayPal for current invoice state (used when no webhook endpoint is exposed)."""
        m = self._milestone(mid)
        if not m["invoice_id"]:
            raise Rejected("No invoice yet.")
        outcome = self._apply("INVOICING.INVOICE.PAID", m["invoice_id"])
        db.audit(self.c, m["project_id"], f"human:{approver}", "polled_paypal", {"milestone": m["seq"], "outcome": outcome})
        return {"outcome": outcome}

    # ---------- reads ----------
    def _project(self, pid):
        r = self.c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        if not r:
            raise Rejected("Unknown project")
        return r

    def _milestone(self, mid):
        r = self.c.execute("SELECT * FROM milestones WHERE id=?", (mid,)).fetchone()
        if not r:
            raise Rejected("Unknown milestone")
        return r

    def view(self, pid: str) -> dict:
        p = dict(self._project(pid))
        risk_raw = p.pop("risk_json", None)
        try:
            p["risk"] = json.loads(risk_raw) if risk_raw else None
        except (TypeError, json.JSONDecodeError):
            p["risk"] = None
        p["milestones"] = [dict(r) for r in self.c.execute("SELECT * FROM milestones WHERE project_id=? ORDER BY seq", (pid,))]
        for ms in p["milestones"]:
            ms.pop("request_id", None)
        p["audit"] = [dict(r) | {"detail": json.loads(r["detail"])} for r in
                      self.c.execute("SELECT actor,action,detail,at FROM audit WHERE project_id=? ORDER BY id", (pid,))]
        return p

    def save_risk(self, pid: str, review: dict, dropped: list[str], approver: str) -> None:
        with db.tx(self.c):
            self.c.execute("UPDATE projects SET risk_json=? WHERE id=?", (json.dumps(review), pid))
            db.audit(self.c, pid, f"human:{approver}", "risk_reviewed",
                     {"risks": len(review.get("risks", [])), "dropped": dropped})

    def list_projects(self) -> dict:
        """Compact portfolio view for the sidebar. No client email or contract text."""
        rows = self.c.execute(
            "SELECT id, client_name, total, currency, status, created FROM projects ORDER BY created DESC"
        ).fetchall()
        out = []
        for p in rows:
            ms = [dict(r) for r in self.c.execute(
                "SELECT seq,title,amount,status,due_date,hold,op_state,invoice_id"
                " FROM milestones WHERE project_id=? ORDER BY seq", (p["id"],))]
            paid_total = sum((Decimal(m["amount"]) for m in ms if m["status"] == "PAID"), Decimal("0"))
            paid_count = sum(1 for m in ms if m["status"] == "PAID")
            next_m = next((m for m in ms if m["status"] != "PAID"), None)
            if p["status"] == "BLOCKED":
                needs = "Fix the blocked plan"
            elif p["status"] == "PROPOSED":
                needs = "Approve the plan"
            elif any(m["op_state"] in ("IN_FLIGHT", "RECONCILIATION_REQUIRED") for m in ms):
                needs = "Reconcile invoice"
            elif any(m["hold"] for m in ms):
                needs = "Resolve a hold"
            elif any(m["status"] == "DRAFTED" for m in ms):
                needs = "Send a draft invoice"
            elif any(m["status"] in ("SENT", "PARTIAL", "MISMATCH") for m in ms):
                needs = "Awaiting payment"
            elif ms and all(m["status"] == "PAID" for m in ms):
                needs = "Complete"
            else:
                needs = "Review"
            out.append({
                "id": p["id"],
                "client_name": p["client_name"],
                "total": p["total"],
                "currency": p["currency"],
                "status": p["status"],
                "paid_total": f"{paid_total:.2f}",
                "paid_count": paid_count,
                "milestone_count": len(ms),
                "next_due": next_m["due_date"] if next_m else None,
                "needs_action": needs,
            })
        return {"projects": out}

    def portfolio_brief(self) -> dict:
        """Deterministic next actions and totals across all projects."""
        rows = self.c.execute(
            "SELECT id, client_name, total, currency, status FROM projects ORDER BY created DESC"
        ).fetchall()
        today = date.today().isoformat()
        outstanding = Decimal("0")
        collected = Decimal("0")
        overdue = 0
        actions: list[dict] = []
        for p in rows:
            ms = [dict(r) for r in self.c.execute(
                "SELECT seq,title,amount,status,due_date,hold,op_state FROM milestones"
                " WHERE project_id=? ORDER BY seq", (p["id"],))]
            for m in ms:
                if m["status"] == "PAID":
                    collected += Decimal(m["amount"])
                elif m["status"] not in ("CANCELLED", "REFUNDED"):
                    outstanding += Decimal(m["amount"])
            next_m = next((m for m in ms if m["status"] not in ("PAID", "CANCELLED", "REFUNDED")), None)
            is_overdue = bool(next_m and next_m["due_date"] < today)
            if is_overdue:
                overdue += 1
            if p["status"] == "BLOCKED":
                action, priority = "Fix the blocked plan", 0
            elif p["status"] == "PROPOSED":
                action, priority = "Approve the plan", 1
            elif any(m["op_state"] in ("IN_FLIGHT", "RECONCILIATION_REQUIRED") for m in ms):
                action, priority = "Reconcile the invoice", 0
            elif any(m["hold"] for m in ms):
                action, priority = "Resolve a hold", 0
            elif any(m["status"] == "DRAFTED" for m in ms):
                action, priority = "Send the draft invoice", 1
            elif any(m["status"] in ("SENT", "PARTIAL", "MISMATCH") for m in ms):
                action, priority = "Follow up on payment", 2
            elif ms and all(m["status"] == "PAID" for m in ms):
                action, priority = "Complete", 3
            else:
                action, priority = "Review", 2
            if action != "Complete":
                actions.append({
                    "project_id": p["id"],
                    "client_name": p["client_name"],
                    "action": action,
                    "amount": next_m["amount"] if next_m else "0.00",
                    "due_date": next_m["due_date"] if next_m else None,
                    "overdue": is_overdue,
                    "priority": priority,
                })
        actions.sort(key=lambda a: (a["priority"], a["due_date"] or "9999-12-31"))
        for a in actions:
            a.pop("priority", None)
        if actions:
            summary = (f"{len(actions)} project{'s' if len(actions) != 1 else ''} need attention. "
                       f"USD {outstanding:.2f} outstanding, USD {collected:.2f} collected, {overdue} overdue.")
        else:
            summary = f"All {len(rows)} projects are up to date. USD {collected:.2f} collected."
        return {
            "generated_at": time.time(),
            "project_count": len(rows),
            "currency": "USD",
            "outstanding_total": f"{outstanding:.2f}",
            "collected_total": f"{collected:.2f}",
            "overdue_count": overdue,
            "summary": summary,
            "actions": actions,
        }
