import pytest

from app import db
from app.extraction import SAMPLE_CONTRACT, ProposedPlan, sample_extract
from app.paypal import SimulatedPayPal
from app.service import PlanEdit, PlanMilestoneEdit, Rejected, Service


def make_service(total="1500.00"):
    pp = SimulatedPayPal()
    svc = Service(db.connect(":memory:"), pp, pp.merchant_email)
    data = sample_extract(SAMPLE_CONTRACT).model_dump()
    data["total"] = total
    pid = svc.propose(ProposedPlan.model_validate(data), SAMPLE_CONTRACT, "fixture")["project_id"]
    return svc, pid


def edit_for(svc, pid):
    p = svc.view(pid)
    return PlanEdit(
        client_name=p["client_name"], client_email=p["client_email"], total=p["total"],
        currency=p["currency"],
        milestones=[PlanMilestoneEdit(id=m["id"], title=m["title"], amount=m["amount"], due_date=m["due_date"])
                    for m in p["milestones"]],
    )


def test_edit_fixes_blocked_plan():
    svc, pid = make_service(total="9.00")
    assert svc.view(pid)["status"] == "BLOCKED"
    edit = edit_for(svc, pid)
    edit.total = "1500.00"
    out = svc.update_plan(pid, edit, "t")
    assert out["errors"] == []
    assert out["project"]["status"] == "PROPOSED"
    assert out["project"]["total"] == "1500.00"


def test_edit_bad_amount_blocks():
    svc, pid = make_service()
    edit = edit_for(svc, pid)
    edit.milestones[0].amount = "abc"
    out = svc.update_plan(pid, edit, "t")
    assert out["project"]["status"] == "BLOCKED"
    assert any("amount" in e for e in out["errors"])


def test_edit_keeps_evidence():
    svc, pid = make_service()
    before = svc.view(pid)["milestones"][0]["evidence"]
    edit = edit_for(svc, pid)
    edit.milestones[0].title = "Design and research"
    edit.milestones[0].amount = "400.00"
    out = svc.update_plan(pid, edit, "t")
    assert out["project"]["milestones"][0]["title"] == "Design and research"
    assert out["project"]["milestones"][0]["evidence"] == before


def test_edit_rejected_after_approval():
    svc, pid = make_service()
    svc.approve(pid, "t")
    with pytest.raises(Rejected, match="only a proposed or blocked"):
        svc.update_plan(pid, edit_for(svc, pid), "t")


def test_edit_cannot_change_milestone_set():
    svc, pid = make_service()
    edit = edit_for(svc, pid)
    edit.milestones.pop()
    with pytest.raises(Rejected, match="milestone set changed"):
        svc.update_plan(pid, edit, "t")


def test_edit_is_audited():
    svc, pid = make_service()
    edit = edit_for(svc, pid)
    edit.client_name = "Acme Labs (revised)"
    svc.update_plan(pid, edit, "t")
    actions = [a["action"] for a in svc.view(pid)["audit"]]
    assert "edited_plan" in actions
