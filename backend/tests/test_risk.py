import json

import pytest

from app import db
from app.extraction import SAMPLE_CONTRACT, sample_extract
from app.paypal import SimulatedPayPal
from app.risk import (
    RiskNote, RiskReview, normalize_severity, parse_risk_review, review_with_llm,
    sample_risk_review, validate_risk_review,
)
from app.service import Service


def service():
    pp = SimulatedPayPal()
    svc = Service(db.connect(":memory:"), pp, pp.merchant_email)
    pid = svc.propose(sample_extract(SAMPLE_CONTRACT), SAMPLE_CONTRACT, "fixture")["project_id"]
    return svc, pid


def test_sample_risk_quotes_are_verbatim():
    review = sample_risk_review(SAMPLE_CONTRACT)
    assert len(review.risks) == 2
    for note in review.risks:
        assert note.evidence.lower() in SAMPLE_CONTRACT.lower()
        assert note.question.endswith("?")


def test_validate_drops_invented_quote():
    review = RiskReview(risks=[
        RiskNote(title="Real", severity="high", evidence="Total project fee: USD 1,500.",
                 why="w", question="q?"),
        RiskNote(title="Invented", severity="high", evidence="This sentence is not in the contract.",
                 why="w", question="q?"),
    ], summary="s")
    clean, dropped = validate_risk_review(review, SAMPLE_CONTRACT)
    assert [r.title for r in clean.risks] == ["Real"]
    assert dropped == ["Invented"]


@pytest.mark.parametrize("raw,want", [
    ("High", "high"), ("critical", "high"), ("Minor", "low"), ("low risk", "low"),
    ("medium", "medium"), ("unknown", "medium"), ("", "medium"),
])
def test_normalize_severity(raw, want):
    assert normalize_severity(raw) == want


def test_parse_risk_review_strips_fence():
    raw = "```json\n" + json.dumps({
        "risks": [{"title": "T", "severity": "High", "evidence": "x", "why": "w", "question": "q?"}],
        "summary": "s",
    }) + "\n```"
    review = parse_risk_review(raw)
    assert review.risks[0].title == "T"


class FakeLLM:
    def __init__(self, answer):
        self.answer = answer

    def complete(self, system, prompt):
        return self.answer


def test_review_with_llm_parses_json():
    answer = json.dumps({
        "risks": [{"title": "T", "severity": "medium", "evidence": "Total project fee: USD 1,500.",
                   "why": "w", "question": "q?"}],
        "summary": "s",
    })
    review = review_with_llm(FakeLLM(answer), SAMPLE_CONTRACT)
    assert review.risks[0].title == "T"


def test_save_risk_and_view():
    svc, pid = service()
    review = sample_risk_review(SAMPLE_CONTRACT)
    svc.save_risk(pid, review.model_dump(), [], "t")
    view = svc.view(pid)
    assert view["risk"]["risks"][0]["title"] == "Extra revisions have no agreed rate"
    assert any(a["action"] == "risk_reviewed" for a in view["audit"])


def test_sample_risk_review_rejects_other_contract():
    with pytest.raises(ValueError, match="sample contract"):
        sample_risk_review("A different contract.")
