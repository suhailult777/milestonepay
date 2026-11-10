"""AI-assisted milestone extraction with strict, deterministic validation.

The model only *proposes*. Every milestone must quote evidence that appears verbatim
in the source text; amounts must be positive USD that sum to the stated total.
"""
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx
from pydantic import BaseModel


class ProposedMilestone(BaseModel):
    title: str
    amount: str
    currency: str
    due_date: str
    evidence: str


class ProposedPlan(BaseModel):
    client_name: str
    client_email: str
    total: str
    currency: str
    milestones: list[ProposedMilestone]
    ambiguities: list[str] = []


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def validate_plan(plan: ProposedPlan, source_text: str, today: date | None = None) -> list[str]:
    """Return a list of blocking errors (empty means the plan may be shown for approval)."""
    today = today or date.today()
    errors: list[str] = []
    src = _norm(source_text)
    if plan.currency != "USD":
        errors.append("Only USD is supported (cross-border PayPal; no INR).")
    if not plan.milestones:
        errors.append("No milestones proposed.")
    try:
        total = Decimal(plan.total)
    except InvalidOperation:
        return errors + [f"Total is not a number: {plan.total!r}"]
    s = Decimal("0")
    for i, m in enumerate(plan.milestones, 1):
        tag = f"Milestone {i}"
        if m.currency != "USD":
            errors.append(f"{tag}: currency must be USD.")
        if not re.fullmatch(r"\d+(\.\d{1,2})?", m.amount):
            errors.append(f"{tag}: amount must be a plain positive number with at most 2 decimals.")
        else:
            amt = Decimal(m.amount)
            if amt <= 0:
                errors.append(f"{tag}: amount must be positive with at most 2 decimals.")
            s += amt
        try:
            if date.fromisoformat(m.due_date) < today:
                errors.append(f"{tag}: due date is in the past.")
        except ValueError:
            errors.append(f"{tag}: due date must be YYYY-MM-DD.")
        if not m.evidence.strip() or _norm(m.evidence) not in src:
            errors.append(f"{tag}: evidence quote not found verbatim in the contract.")
        else:
            nums = {Decimal(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", m.evidence)}
            try:
                if Decimal(m.amount) not in nums:
                    errors.append(f"{tag}: amount {m.amount} does not appear in its evidence quote.")
            except InvalidOperation:
                pass
            if m.due_date not in m.evidence:
                errors.append(f"{tag}: due date {m.due_date} not in evidence quote; confirm manually.")
            ev = _norm(m.evidence)
            if re.search(r"\b(up to|between|maximum|max\.?|minimum|min\.?|no more than|not to exceed|range)\b", ev) or \
                    re.search(r"(?:usd|\$)\s*\d[\d,.]*\s*(?:-|–|to)\s*(?:usd|\$)?\s*\d", ev):
                errors.append(f"{tag}: evidence looks like a range or limit; confirm the exact amount manually.")
    if s != total:
        errors.append(f"Milestones sum to {s} but total is {total}.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", plan.client_email or ""):
        errors.append("Client email missing or invalid.")
    return errors


SAMPLE_CONTRACT = """Statement of Work - Acme Labs (billing@acme-labs.example) and the developer.
Total project fee: USD 1,500.
Milestone 1: Design mockups, USD 400, due 2026-11-20.
Milestone 2: Working MVP, USD 700, due 2026-12-05.
Milestone 3: Launch and handover, USD 400, due 2026-12-20.
Revisions beyond two rounds will be billed separately at a rate to be agreed."""


def sample_extract(source_text: str) -> ProposedPlan:
    """Labelled fixture output for the bundled sample contract. Not live AI."""
    if _norm(source_text) != _norm(SAMPLE_CONTRACT):
        raise ValueError("Sample extractor only supports the bundled sample contract. Set LLM_PROVIDER=ollama for other text.")
    return ProposedPlan(
        client_name="Acme Labs", client_email="billing@acme-labs.example", total="1500.00", currency="USD",
        milestones=[
            ProposedMilestone(title="Design mockups", amount="400.00", currency="USD", due_date="2026-11-20",
                              evidence="Milestone 1: Design mockups, USD 400, due 2026-11-20."),
            ProposedMilestone(title="Working MVP", amount="700.00", currency="USD", due_date="2026-12-05",
                              evidence="Milestone 2: Working MVP, USD 700, due 2026-12-05."),
            ProposedMilestone(title="Launch and handover", amount="400.00", currency="USD", due_date="2026-12-20",
                              evidence="Milestone 3: Launch and handover, USD 400, due 2026-12-20."),
        ],
        ambiguities=["Extra revisions are billed 'at a rate to be agreed' - not invoiced; confirm with client."],
    )


PROMPT = """Extract a milestone payment plan from the contract. Reply with JSON only:
{"client_name":str,"client_email":str,"total":"0.00","currency":"USD",
 "milestones":[{"title":str,"amount":"0.00","currency":"USD","due_date":"YYYY-MM-DD","evidence":"exact sentence copied from contract"}],
 "ambiguities":[str]}
Copy evidence verbatim. List anything unclear in ambiguities. Do not invent amounts.
CONTRACT:
"""


def ollama_extract(source_text: str, base_url: str, model: str, client: httpx.Client | None = None) -> ProposedPlan:
    """Local, free model via Ollama's /api/chat with JSON output."""
    c = client or httpx.Client(timeout=120)
    r = c.post(f"{base_url}/api/chat", json={
        "model": model, "stream": False, "format": "json",
        "messages": [{"role": "user", "content": PROMPT + source_text}],
    })
    r.raise_for_status()
    return ProposedPlan.model_validate(json.loads(r.json()["message"]["content"]))
