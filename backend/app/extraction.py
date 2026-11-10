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


_PUNCT = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\xa0": " ",
})


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(_PUNCT)).strip().lower()


def _date_variants(iso: str) -> list[str]:
    """Common ways a contract writes a date, not just the ISO form."""
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return [iso]
    return [
        iso,
        d.strftime("%d %B %Y"), d.strftime("%d %b %Y"),
        f"{d.day} {d.strftime('%B')} {d.year}", f"{d.day} {d.strftime('%b')} {d.year}",
        d.strftime("%B %d, %Y"), d.strftime("%b %d, %Y"),
        f"{d.strftime('%B')} {d.day}, {d.year}", f"{d.strftime('%b')} {d.day}, {d.year}",
        d.strftime("%d/%m/%Y"), d.strftime("%m/%d/%Y"),
    ]


def _date_in_evidence(iso: str, evidence: str) -> bool:
    ev = _norm(evidence)
    return any(_norm(v) in ev for v in _date_variants(iso))


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
            if not _date_in_evidence(m.due_date, m.evidence):
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

Parties. This Statement of Work is between Acme Labs (billing@acme-labs.example), the client, and the developer.

Scope. The developer will design the product interface, build a working MVP, and complete launch handover. The work includes design mockups, front-end implementation, and a launch handover session. The client will provide content, product access, and feedback within two business days.

Milestone 1: Design mockups, USD 400, due 2026-11-20.
Milestone 2: Working MVP, USD 700, due 2026-12-05.
Milestone 3: Launch and handover, USD 400, due 2026-12-20.

Payment terms. Total project fee: USD 1,500. Payment follows the milestone schedule above. Each invoice is due on the milestone date. The client pays each invoice before the next milestone unlocks. The fee excludes third-party subscriptions and travel.

Revisions. Revisions beyond two rounds will be billed separately at a rate to be agreed.

Acceptance. The client will review each deliverable within five business days and send written acceptance or one consolidated change list.

Governing terms. This agreement is governed by the laws of India. Either party may terminate for material breach after ten business days' written notice."""


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


EXTRACTION_SYSTEM = """You extract milestone payment plans from freelance contracts.
You only return JSON. You never approve, send, or move money.
Every milestone must include an exact sentence copied from the contract as evidence.
Do not invent amounts, dates, clients, or emails. Put anything unclear in ambiguities."""

PROMPT = """Extract a milestone payment plan from the contract. Reply with JSON only:
{"client_name":str,"client_email":str,"total":"0.00","currency":"USD",
 "milestones":[{"title":str,"amount":"0.00","currency":"USD","due_date":"YYYY-MM-DD","evidence":"exact sentence copied from contract"}],
 "ambiguities":[str]}
Copy evidence verbatim. Use ISO dates (YYYY-MM-DD) in due_date, but keep the contract's original date wording in evidence.
List anything unclear in ambiguities. Do not invent amounts.
CONTRACT:
"""


def build_extraction_prompt(source_text: str, today: date | None = None) -> str:
    today = today or date.today()
    return f"Today is {today.isoformat()}.\n{PROMPT}{source_text}"


def parse_plan(raw: str) -> ProposedPlan:
    if not raw or not raw.strip():
        raise ValueError("model returned an empty answer")
    text = raw.strip()
    if text.startswith("```"):
        # Some free models wrap JSON in a markdown fence even when asked not to.
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("model did not return valid JSON") from e
    if not isinstance(data, dict):
        raise ValueError("model JSON is not an object")
    return ProposedPlan.model_validate(data)


def extract_with_llm(llm, source_text: str, today: date | None = None) -> ProposedPlan:
    """One extraction, plus one repair attempt if the model returns invalid JSON."""
    prompt = build_extraction_prompt(source_text, today)
    raw = llm.complete(EXTRACTION_SYSTEM, prompt)
    try:
        return parse_plan(raw)
    except ValueError as first:
        repair = (
            f"{prompt}\n\nYour previous answer was invalid: {first}."
            " Return only valid JSON with the exact schema. Do not add prose."
        )
        raw2 = llm.complete(EXTRACTION_SYSTEM, repair)
        try:
            return parse_plan(raw2)
        except ValueError as second:
            raise ValueError(f"model returned an invalid plan twice: {second}") from second


def ollama_extract(source_text: str, base_url: str, model: str, client: httpx.Client | None = None) -> ProposedPlan:
    """Backwards-compatible wrapper around the shared Ollama provider."""
    from .llm import OllamaLLM

    return extract_with_llm(OllamaLLM(base_url, model, http=client), source_text)
