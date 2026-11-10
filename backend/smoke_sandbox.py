"""REAL PayPal SANDBOX smoke test. Reads secrets from env only; prints no tokens or headers.

Env: PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_MERCHANT_EMAIL (sandbox business),
     SMOKE_BUYER_EMAIL (sandbox personal, ideally US). Optional: SMOKE_STEP=create|status <invoice_id>
Never touches production (adapter asserts sandbox base URL). send_to_recipient=false: no email sent.
"""
import os, sys, time, uuid
sys.path.insert(0, os.path.dirname(__file__))
from app.paypal import PayPalError, SandboxPayPal

def _load_env_file(path):
    """Load KEY=VALUE lines into os.environ without printing anything."""
    if os.path.exists(path):
        for ln in open(path):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.removeprefix("export ").split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

_load_env_file(os.path.join(os.path.dirname(__file__), "..", ".env.sandbox"))

need = ["PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_MERCHANT_EMAIL", "SMOKE_BUYER_EMAIL"]
missing = [k for k in need if not os.getenv(k)]
if missing:
    sys.exit(f"missing env: {', '.join(missing)}")
pp = SandboxPayPal(os.environ["PAYPAL_CLIENT_ID"], os.environ["PAYPAL_CLIENT_SECRET"], os.getenv("PAYPAL_WEBHOOK_ID", ""))

def summary(inv):
    return {"id": inv.get("id"), "status": inv.get("status"), "amount": inv.get("amount"),
            "paid": (inv.get("payments") or {}).get("paid_amount"),
            "invoicer": (inv.get("invoicer") or {}).get("email_address"),
            "number": (inv.get("detail") or {}).get("invoice_number")}

try:
    if len(sys.argv) > 2 and sys.argv[1] == "status":
        print(summary(pp.get_invoice(sys.argv[2]))); sys.exit(0)
    number = f"MP-SMOKE-{int(time.time())}"
    rid = str(uuid.uuid4())
    iid = pp.create_draft_invoice(request_id=rid, merchant_email=os.environ["PAYPAL_MERCHANT_EMAIL"],
                                  recipient_email=os.environ["SMOKE_BUYER_EMAIL"], title="Smoke milestone",
                                  amount="1.00", currency="USD", due_date="2026-12-31", number=number)
    print("created", iid, number)
    print("search_by_number", pp.find_by_number(number))
    link = pp.send_invoice(iid, f"send-{rid}")
    print("sent (no email). payer link:", link)
    print(summary(pp.get_invoice(iid)))
    import json, datetime
    art = {"at_utc": datetime.datetime.utcnow().isoformat() + "Z", "endpoint": "https://api-m.sandbox.paypal.com/v2/invoicing",
           "invoice_id": iid, "invoice_number": number, "payer_link": link, "expected": "1.00 USD",
           "merchant": os.environ["PAYPAL_MERCHANT_EMAIL"], "buyer": os.environ["SMOKE_BUYER_EMAIL"],
           "status_after_send": pp.get_invoice(iid).get("status")}
    os.makedirs("evals", exist_ok=True)
    json.dump(art, open("evals/sandbox_smoke_artifact.json", "w"), indent=1)
    print("Next: buyer pays via link in sandbox, then: python smoke_sandbox.py status", iid)
except PayPalError as e:
    print("PayPal error", e.status, "debug_id", e.debug_id); sys.exit(1)
