import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from . import config, db
from .extraction import SAMPLE_CONTRACT, extract_with_llm, sample_extract
from .llm import LLMError, build_llm
from .paypal import SandboxPayPal, SimulatedPayPal
from .risk import sample_risk_review, review_with_llm, validate_risk_review
from .service import PlanEdit, Rejected, Service

S = config.load()
conn = db.connect(S.db_path)
if S.mode == "live":
    pp = SandboxPayPal(S.paypal_client_id, S.paypal_client_secret, S.paypal_webhook_id, S.paypal_base)
    merchant = S.paypal_merchant_email
else:
    pp = SimulatedPayPal()
    merchant = pp.merchant_email
svc = Service(conn, pp, merchant)
app = FastAPI(title="MilestonePay")
ADMIN_TOKEN = os.getenv("MP_ADMIN_TOKEN", "")
_llm = None


def get_llm():
    """Build the provider chain on first use; sample mode never needs a key."""
    global _llm
    if _llm is None:
        _llm = build_llm(S)
    return _llm


def ai_label() -> str:
    if S.llm_provider == "sample":
        return "Fixture output (sample, not live AI)"
    if S.llm_provider == "ollama":
        return f"Local Ollama ({S.llm_model})"
    if S.llm_provider == "openrouter":
        return "OpenRouter free model with Ollama fallback"
    return "OpenRouter if a key is present, else local Ollama"


def require_token(x_mp_token: str = Header(default="")) -> None:
    """Local-only guard for state-changing routes. Not a substitute for real auth + CSRF before any public exposure."""
    if not ADMIN_TOKEN or not secrets.compare_digest(x_mp_token, ADMIN_TOKEN):
        raise HTTPException(401, "missing or bad X-MP-Token")


AUTH = [Depends(require_token)]
MAX_WEBHOOK_BYTES = 64 * 1024


class Extract(BaseModel):
    text: str


class Who(BaseModel):
    approver: str = "freelancer"
    confirm: bool = False


def _wrap(fn, *a):
    try:
        return fn(*a)
    except Rejected as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/info")
def info():
    return {"mode": S.mode, "llm_provider": S.llm_provider,
            "labels": {"paypal": "PayPal SANDBOX (real sandbox API, fake funds)" if S.mode == "live" else "SIMULATED PayPal (sample mode)",
                       "ai": ai_label()},
            "sample_contract": SAMPLE_CONTRACT}


@app.post("/api/projects", dependencies=AUTH)
def create(body: Extract):
    def run():
        if S.llm_provider == "sample":
            plan, src = sample_extract(body.text), "fixture"
        else:
            try:
                llm = get_llm()
                plan = extract_with_llm(llm, body.text)
                src = f"llm:{llm.last_used or S.llm_provider}"
            except LLMError as e:
                raise HTTPException(502, str(e))
            except ValueError as e:
                raise HTTPException(422, str(e))
        return svc.propose(plan, body.text, src)
    return _wrap(run)


@app.get("/api/projects", dependencies=AUTH)
def projects():
    return _wrap(svc.list_projects)


@app.get("/api/brief", dependencies=AUTH)
def brief():
    return _wrap(svc.portfolio_brief)


@app.get("/api/projects/{pid}", dependencies=AUTH)
def get(pid: str):
    return _wrap(svc.view, pid)


@app.post("/api/projects/{pid}/approve", dependencies=AUTH)
def approve(pid: str, w: Who):
    _wrap(svc.approve, pid, w.approver)
    return svc.view(pid)


@app.post("/api/projects/{pid}/risk", dependencies=AUTH)
def risk(pid: str):
    def run():
        p = svc.view(pid)
        if S.llm_provider == "sample":
            review = sample_risk_review(p["source_text"])
        else:
            try:
                review = review_with_llm(get_llm(), p["source_text"])
            except LLMError as e:
                raise HTTPException(502, str(e))
        clean, dropped = validate_risk_review(review, p["source_text"])
        svc.save_risk(pid, clean.model_dump(), dropped, "You")
        return {"risk": clean.model_dump(), "dropped": dropped}
    return _wrap(run)


@app.put("/api/projects/{pid}/plan", dependencies=AUTH)
def edit_plan(pid: str, body: PlanEdit):
    return _wrap(svc.update_plan, pid, body, "You")


@app.post("/api/milestones/{mid}/draft", dependencies=AUTH)
def draft(mid: str, w: Who):
    return _wrap(svc.draft_invoice, mid, w.approver)


@app.post("/api/milestones/{mid}/send", dependencies=AUTH)
def send(mid: str, w: Who):
    return _wrap(svc.send_invoice, mid, w.approver, w.confirm)


@app.post("/api/milestones/{mid}/reconcile", dependencies=AUTH)
def reconcile(mid: str, w: Who):
    return _wrap(svc.reconcile_creation, mid, w.approver)


@app.post("/api/milestones/{mid}/refresh", dependencies=AUTH)
def refresh(mid: str, w: Who):
    return _wrap(svc.refresh_from_paypal, mid, w.approver)


@app.post("/api/webhooks/paypal")
async def webhook(req: Request):
    raw = await req.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(413, "webhook body too large")
    try:
        return svc.handle_webhook(dict(req.headers), raw)
    except Rejected as e:
        raise HTTPException(400, str(e))


@app.post("/api/simulate/pay/{mid}", dependencies=AUTH)
def simulate_pay(mid: str):
    """Sample mode only: simulate the client paying and PayPal sending a signed webhook."""
    if S.mode != "sample":
        raise HTTPException(404)
    import json
    m = conn.execute("SELECT * FROM milestones WHERE id=?", (mid,)).fetchone()
    if not m or not m["invoice_id"]:
        raise HTTPException(409, "No invoice")
    ev = pp.simulate_payment(m["invoice_id"], m["amount"])
    return svc.handle_webhook({"paypal-transmission-sig": SimulatedPayPal.SIM_SIG}, json.dumps(ev).encode())


@app.post("/api/simulate/timeout/{mid}", dependencies=AUTH)
def simulate_timeout(mid: str):
    """Sample mode only: arm the next draft create to time out after PayPal accepts it."""
    if S.mode != "sample" or not isinstance(pp, SimulatedPayPal):
        raise HTTPException(404)
    m = conn.execute("SELECT * FROM milestones WHERE id=?", (mid,)).fetchone()
    if not m or m["invoice_id"] or m["op_state"] != "NONE":
        raise HTTPException(409, "Timeout hook needs a milestone with no invoice and no pending create.")
    pp.fail_next = "timeout_after_accept"
    return {"armed": True, "note": "Next draft create will time out after PayPal accepts. Use Create draft invoice, then Reconcile."}


@app.post("/api/simulate/forged/{mid}", dependencies=AUTH)
def simulate_forged(mid: str):
    if S.mode != "sample":
        raise HTTPException(404)
    import json
    m = conn.execute("SELECT * FROM milestones WHERE id=?", (mid,)).fetchone()
    ev = {"id": "WH-FORGED", "event_type": "INVOICING.INVOICE.PAID", "resource": {"invoice": {"id": m["invoice_id"]}}}
    try:
        return svc.handle_webhook({"paypal-transmission-sig": "forged"}, json.dumps(ev).encode())
    except Rejected as e:
        return {"outcome": "rejected", "reason": str(e)}
