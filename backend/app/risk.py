"""Evidence-backed contract risk review.

The model may only surface a risk with a quote copied from the contract.
Fixed code drops any note whose quote is not found. This is advisory, not legal advice.
"""
from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel

from .extraction import SAMPLE_CONTRACT, _norm


class RiskNote(BaseModel):
    title: str
    severity: str = "medium"
    evidence: str
    why: str
    question: str


class RiskReview(BaseModel):
    risks: list[RiskNote] = []
    summary: str = ""


RISK_SYSTEM = """You review freelance contracts for payment and delivery risk.
You only return JSON. You never give legal advice. Every risk must include an exact sentence copied from the contract as evidence.
Do not invent clauses, amounts, dates, or parties. If the contract does not support a risk, leave it out.
Focus on payment ambiguity, scope creep, unlimited revisions, late payment, termination, IP ownership, expenses, and currency."""

RISK_PROMPT = """Review this contract for risks that could cause a payment dispute.
Reply with JSON only:
{"risks":[{"title":str,"severity":"high|medium|low","evidence":"exact sentence from the contract","why":str,"question":str}],"summary":str}
Rules:
- Copy evidence verbatim. A quote that is not in the contract will be dropped.
- At most 6 risks. Prefer fewer, stronger notes.
- question must be a short, specific question the freelancer can ask the client.
- Do not give legal advice. Say what to clarify, not what the law is.
CONTRACT:
"""


def build_risk_prompt(source_text: str) -> str:
    return RISK_PROMPT + source_text


def parse_risk_review(raw: str) -> RiskReview:
    if not raw or not raw.strip():
        raise ValueError("model returned an empty risk review")
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3].rstrip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("risk review was not valid JSON") from e
    if not isinstance(data, dict):
        raise ValueError("risk review JSON is not an object")
    return RiskReview.model_validate(data)


def normalize_severity(value: str) -> str:
    v = (value or "").strip().lower()
    if v.startswith(("high", "critical", "severe")):
        return "high"
    if v.startswith(("low", "minor")):
        return "low"
    return "medium"


def validate_risk_review(review: RiskReview, source_text: str) -> tuple[RiskReview, list[str]]:
    """Keep only notes whose evidence quote appears verbatim in the contract."""
    source = _norm(source_text)
    kept: list[RiskNote] = []
    dropped: list[str] = []
    for note in review.risks[:6]:
        quote = _norm(note.evidence)
        if not quote or quote not in source:
            dropped.append(note.title)
            continue
        kept.append(note.model_copy(update={"severity": normalize_severity(note.severity)}))
    return RiskReview(risks=kept, summary=review.summary.strip()), dropped


def sample_risk_review(source_text: str) -> RiskReview:
    """Deterministic demo review for the bundled sample contract. Not live AI."""
    if _norm(source_text) != _norm(SAMPLE_CONTRACT):
        raise ValueError("Sample risk review only supports the bundled sample contract. Use a live provider for other text.")
    return RiskReview(
        risks=[
            RiskNote(
                title="Extra revisions have no agreed rate",
                severity="high",
                evidence="Revisions beyond two rounds will be billed separately at a rate to be agreed.",
                why="The rate is open-ended, so the amount for extra work can be disputed after it is done.",
                question="What is the hourly rate for extra revisions, and is there a cap on total revision cost?",
            ),
            RiskNote(
                title="Launch has no acceptance criteria",
                severity="medium",
                evidence="Milestone 3: Launch and handover, USD 400, due 2026-12-20.",
                why="The contract does not define what must be delivered or signed off for launch and handover.",
                question="What exactly counts as launched and handed over for milestone 3?",
            ),
        ],
        summary="Two clauses need a written answer before work starts: the extra-revision rate and the launch acceptance criteria.",
    )


class LLM(Protocol):
    def complete(self, system: str, prompt: str) -> str: ...


def review_with_llm(llm: LLM, source_text: str) -> RiskReview:
    raw = llm.complete(RISK_SYSTEM, build_risk_prompt(source_text))
    return parse_risk_review(raw)
