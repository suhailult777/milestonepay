import json
import sqlite3
import time
import uuid
from decimal import Decimal

from . import db
from .extraction import ProposedPlan, validate_plan
import httpx

from .paypal import PayPalError, PayPalPort


class Rejected(Exception):
    pass


HANDLED = {"INVOICING.INVOICE.PAID", "INVOICING.INVOICE.REFUNDED", "INVOICING.INVOICE.CANCELLED"}


class Service:
    def __init__(self, conn: sqlite3.Connection, paypal: PayPalPort, merchant_email: str):
        self.c, self.pp, self.merchant = conn, paypal, merchant_email

    # ---------- plan ----------
    def propose(self, plan: ProposedPlan, source_text: str, extraction_source: str) -> dict:
        errors = validate_plan(plan, source_text)
        pid = uuid.uuid4().hex[:12]
        status = "BLOCKED" if errors else "PROPOSED"
        self.c.execute("INSERT INTO projects VALUES(?,?,?,?,?,?,?,?,?)",
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
        self.c.execute("UPDATE projects SET status='APPROVED' WHERE id=?", (pid,))
        db.audit(self.c, pid, f"human:{approver}", "approved_plan", {})

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
        self.c.execute("UPDATE milestones SET invoice_id=?, status='DRAFTED', op_state='DONE' WHERE id=?", (iid, mid))
        db.audit(self.c, p["id"], f"human:{approver}", "drafted_invoice",
                 {"milestone": m["seq"], "invoice_id": iid, "paypal_request_id": m["request_id"], "number": number})
        return {"invoice_id": iid, "duplicate": False}

    def _ambiguous(self, m, p, why: str) -> dict:
        self.c.execute("UPDATE milestones SET op_state='RECONCILIATION_REQUIRED', op_note=? WHERE id=?", (why[:200], m["id"]))
        db.audit(self.c, p["id"], "system", "create_outcome_unknown", {"milestone": m["seq"], "error": why[:200]})
        raise Rejected("PayPal outcome unknown (timeout or server error). Automatic retry is blocked; run reconciliation.")

    def reconcile_creation(self, mid: str, approver: str) -> dict:
        """Human-triggered. Covers timeouts and crashes left IN_FLIGHT. Looks up by our unique invoice number."""
        m = self._milestone(mid)
        if m["op_state"] not in ("RECONCILIATION_REQUIRED", "IN_FLIGHT"):
            raise Rejected(f"Nothing to reconcile (state {m['op_state']}).")
        found = self.pp.find_by_number(f"MP-{m['project_id']}-{m['seq']}")
        if len(found) == 1:
            self.c.execute("UPDATE milestones SET invoice_id=?, status='DRAFTED', op_state='DONE' WHERE id=?", (found[0], mid))
            result = {"recovered_invoice_id": found[0]}
        elif not found:
            self.c.execute("UPDATE milestones SET op_state='NONE' WHERE id=?", (mid,))
            result = {"recovered_invoice_id": None, "note": "No invoice exists at PayPal; creation may be retried by a human."}
        else:
            result = {"error": "Multiple PayPal invoices share this number; resolve manually in PayPal.", "ids": found}
        db.audit(self.c, m["project_id"], f"human:{approver}", "reconciled_creation", result)
        return result

    def send_invoice(self, mid: str, approver: str, confirm: bool) -> dict:
        m = self._milestone(mid)
        if not confirm:
            raise Rejected("Explicit confirmation required to send.")
        if m["status"] != "DRAFTED":
            raise Rejected(f"Milestone is {m['status']}; only DRAFTED can be sent.")
        if m["hold"] or not self._prior_all_paid(m):
            raise Rejected("On hold: an earlier milestone is no longer confirmed PAID.")
        link = self.pp.send_invoice(m["invoice_id"], f"send-{m['request_id']}")
        self.c.execute("UPDATE milestones SET status='SENT', pay_link=? WHERE id=?", (link, mid))
        db.audit(self.c, m["project_id"], f"human:{approver}", "sent_invoice",
                 {"milestone": m["seq"], "invoice_id": m["invoice_id"]})
        return {"pay_link": link}

    # ---------- webhook ----------
    def handle_webhook(self, headers: dict[str, str], raw: bytes) -> dict:
        if not self.pp.verify_webhook(headers, raw):
            db.audit(self.c, None, "paypal", "webhook_rejected", {"reason": "signature"})
            raise Rejected("Webhook signature verification failed.")
        ev = json.loads(raw)
        eid, etype = ev.get("id"), ev.get("event_type")
        res = ev.get("resource") or {}
        inv_id = (res.get("invoice") or res).get("id")
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
        self.c.execute("UPDATE milestones SET status=?, paid_amount=? WHERE id=?", (new, paid.get("value"), m["id"]))
        if m["status"] == "PAID" and new != "PAID":
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
        p["milestones"] = [dict(r) for r in self.c.execute("SELECT * FROM milestones WHERE project_id=? ORDER BY seq", (pid,))]
        for ms in p["milestones"]:
            ms.pop("request_id", None)
        p["audit"] = [dict(r) | {"detail": json.loads(r["detail"])} for r in
                      self.c.execute("SELECT actor,action,detail,at FROM audit WHERE project_id=? ORDER BY id", (pid,))]
        return p
