import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mode: str  # "sample" (labelled fixtures, no network) or "live" (PayPal sandbox)
    paypal_client_id: str
    paypal_client_secret: str
    paypal_webhook_id: str
    paypal_merchant_email: str
    llm_provider: str  # "sample" or "ollama"
    llm_base_url: str
    llm_model: str
    db_path: str

    @property
    def paypal_base(self) -> str:
        # Sandbox only. Production is intentionally not supported.
        return "https://api-m.sandbox.paypal.com"


def load() -> Settings:
    s = Settings(
        mode=os.getenv("MP_MODE", "sample"),
        paypal_client_id=os.getenv("PAYPAL_CLIENT_ID", ""),
        paypal_client_secret=os.getenv("PAYPAL_CLIENT_SECRET", ""),
        paypal_webhook_id=os.getenv("PAYPAL_WEBHOOK_ID", ""),
        paypal_merchant_email=os.getenv("PAYPAL_MERCHANT_EMAIL", ""),
        llm_provider=os.getenv("LLM_PROVIDER", "sample"),
        llm_base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434"),
        llm_model=os.getenv("LLM_MODEL", "qwen2.5:3b-instruct"),
        db_path=os.getenv("MP_DB", "milestonepay.sqlite3"),
    )
    if s.mode not in ("sample", "live"):
        raise ValueError("MP_MODE must be sample or live")
    if s.mode == "live":
        missing = [k for k, v in {
            "PAYPAL_CLIENT_ID": s.paypal_client_id,
            "PAYPAL_CLIENT_SECRET": s.paypal_client_secret,
            "PAYPAL_WEBHOOK_ID": s.paypal_webhook_id,
            "PAYPAL_MERCHANT_EMAIL": s.paypal_merchant_email,
        }.items() if not v]
        if missing:
            raise ValueError(f"live mode needs: {', '.join(missing)}")
    return s
