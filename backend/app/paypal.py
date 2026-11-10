"""PayPal sandbox adapter (Invoicing v2 + webhook verification).

Docs: https://developer.paypal.com/docs/api/invoicing/v2/
      https://developer.paypal.com/docs/api/webhooks/v1/#verify-webhook-signature
Secrets are read from env only and never logged.
"""
import json
import time
import uuid
from typing import Protocol

import httpx


class PayPalError(Exception):
    def __init__(self, status: int, debug_id: str | None, message: str):
        super().__init__(f"PayPal {status} debug_id={debug_id}: {message}")
        self.status, self.debug_id = status, debug_id


class PayPalPort(Protocol):
    def create_draft_invoice(self, *, request_id: str, merchant_email: str, recipient_email: str,
                             title: str, amount: str, currency: str, due_date: str, number: str) -> str: ...
    def send_invoice(self, invoice_id: str, request_id: str) -> str | None: ...
    def get_invoice(self, invoice_id: str) -> dict: ...
    def verify_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool: ...
    def find_by_number(self, number: str) -> list[str]: ...


HEADER_MAP = {
    "auth_algo": "paypal-auth-algo", "cert_url": "paypal-cert-url",
    "transmission_id": "paypal-transmission-id", "transmission_sig": "paypal-transmission-sig",
    "transmission_time": "paypal-transmission-time",
}


class SandboxPayPal:
    def __init__(self, client_id: str, secret: str, webhook_id: str,
                 base: str = "https://api-m.sandbox.paypal.com", http: httpx.Client | None = None):
        if "sandbox" not in base:
            raise ValueError("production is not supported; base URL must be a PayPal sandbox host")
        self._id, self._secret, self._webhook_id, self._base = client_id, secret, webhook_id, base
        self._http = http or httpx.Client(timeout=30)
        self._token: str | None = None
        self._exp = 0.0

    def _auth(self) -> dict:
        if not self._token or time.time() > self._exp - 60:
            r = self._http.post(f"{self._base}/v1/oauth2/token", auth=(self._id, self._secret),
                                data={"grant_type": "client_credentials"})
            self._check(r)
            j = r.json()
            self._token, self._exp = j["access_token"], time.time() + int(j.get("expires_in", 300))
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    @staticmethod
    def _check(r: httpx.Response) -> None:
        if r.status_code >= 400:
            dbg, msg = None, r.text[:300]
            try:
                j = r.json()
                dbg = j.get("debug_id")
                issues = [d.get("issue") for d in j.get("details", []) if d.get("issue")]
                msg = f"{j.get('name')}: {', '.join(issues) or j.get('message')}"
            except Exception:
                pass
            raise PayPalError(r.status_code, dbg, msg)

    def _req(self, method: str, path: str, *, request_id: str | None = None, body=None, content=None,
             prefer: str | None = None) -> httpx.Response:
        h = self._auth()
        if request_id:
            h["PayPal-Request-Id"] = request_id
        if prefer:
            h["Prefer"] = prefer
        for attempt in range(4):
            r = self._http.request(method, f"{self._base}{path}", headers=h, json=body, content=content)
            if r.status_code != 429 and r.status_code < 500:
                break
            time.sleep(min(2 ** attempt, 8))
        self._check(r)
        return r

    def create_draft_invoice(self, *, request_id, merchant_email, recipient_email, title, amount, currency,
                             due_date, number) -> str:
        body = {
            "detail": {"currency_code": currency, "invoice_number": number,
                       "payment_term": {"due_date": due_date}, "note": f"Milestone: {title}"},
            "invoicer": {"email_address": merchant_email},
            "primary_recipients": [{"billing_info": {"email_address": recipient_email}}],
            "items": [{"name": title, "quantity": "1", "unit_amount": {"currency_code": currency, "value": amount}}],
            "configuration": {"allow_tip": False, "partial_payment": {"allow_partial_payment": False}},
        }
        r = self._req("POST", "/v2/invoicing/invoices", request_id=request_id, body=body,
                      prefer="return=representation")
        j = r.json()
        if "id" in j:
            return j["id"]
        return j["href"].rstrip("/").split("/")[-1]

    def send_invoice(self, invoice_id, request_id) -> str | None:
        # send_to_recipient=False: PayPal does not email anyone; we display the payer link.
        r = self._req("POST", f"/v2/invoicing/invoices/{invoice_id}/send", request_id=request_id,
                      body={"send_to_invoicer": False, "send_to_recipient": False})
        try:
            return r.json().get("href")
        except Exception:
            return None

    def get_invoice(self, invoice_id) -> dict:
        return self._req("GET", f"/v2/invoicing/invoices/{invoice_id}").json()

    def find_by_number(self, number) -> list[str]:
        r = self._req("POST", "/v2/invoicing/search-invoices?page_size=10", body={"invoice_number": number})
        return [i["id"] for i in r.json().get("items", [])]

    def verify_webhook(self, headers, raw_body) -> bool:
        low = {k.lower(): v for k, v in headers.items()}
        fields = {k: low.get(h, "") for k, h in HEADER_MAP.items()}
        if not all(fields.values()) or not self._webhook_id:
            return False
        # API expects webhook_event as a JSON object. We splice the received bytes in as that
        # object (after checking they parse as one) so whitespace/key order are not altered.
        if not isinstance(json.loads(raw_body), dict):
            return False
        prefix = json.dumps({**fields, "webhook_id": self._webhook_id})[:-1]
        content = prefix.encode() + b', "webhook_event": ' + raw_body + b"}"
        try:
            r = self._req("POST", "/v1/notifications/verify-webhook-signature", content=content)
        except PayPalError:
            return False  # treat any verification error as not verified (fail closed)
        return r.json().get("verification_status") == "SUCCESS"


class SimulatedPayPal:
    """SAMPLE MODE ONLY. In-memory stand-in; nothing here touches PayPal."""
    SIM_SIG = "SIMULATED-SIGNATURE"

    def __init__(self, merchant_email: str = "merchant@sample.example"):
        self.merchant_email = merchant_email
        self.invoices: dict[str, dict] = {}
        self.by_request: dict[str, str] = {}
        self.create_calls = 0
        self.fail_next: str | None = None  # test hook: "timeout_after_accept" | "reject" | "timeout_before"

    def create_draft_invoice(self, *, request_id, merchant_email, recipient_email, title, amount, currency,
                             due_date, number) -> str:
        self.create_calls += 1
        mode, self.fail_next = self.fail_next, None
        if mode == "timeout_before":
            raise httpx.ReadTimeout("simulated timeout before PayPal received request")
        if mode == "reject":
            raise PayPalError(422, "sim-debug", "simulated validation error")
        iid = f"SIM-INV-{uuid.uuid4().hex[:8].upper()}"
        self.invoices[iid] = {"id": iid, "status": "DRAFT", "invoicer": {"email_address": merchant_email},
                              "amount": {"currency_code": currency, "value": amount},
                              "primary_recipients": [{"billing_info": {"email_address": recipient_email}}],
                              "payments": {"paid_amount": {"currency_code": currency, "value": "0.00"}}}
        self.by_request[request_id] = iid
        self.invoices[iid]["number"] = number
        if mode == "timeout_after_accept":
            raise httpx.ReadTimeout("simulated timeout after PayPal accepted request")
        return iid

    def find_by_number(self, number) -> list[str]:
        return [i for i, v in self.invoices.items() if v.get("number") == number]

    def send_invoice(self, invoice_id, request_id) -> str | None:
        self.invoices[invoice_id]["status"] = "SENT"
        return f"simulated://pay/{invoice_id}"

    def get_invoice(self, invoice_id) -> dict:
        return json.loads(json.dumps(self.invoices[invoice_id]))

    def verify_webhook(self, headers, raw_body) -> bool:
        return {k.lower(): v for k, v in headers.items()}.get("paypal-transmission-sig") == self.SIM_SIG

    # --- simulation helpers ---
    def simulate_payment(self, invoice_id: str, value: str, status: str = "PAID") -> dict:
        inv = self.invoices[invoice_id]
        inv["status"] = status
        inv["payments"]["paid_amount"]["value"] = value
        return {"id": f"WH-SIM-{uuid.uuid4().hex[:10]}", "event_type": "INVOICING.INVOICE.PAID",
                "resource": {"invoice": {"id": invoice_id}}}
