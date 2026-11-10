import json

from app import db
from app.extraction import SAMPLE_CONTRACT, sample_extract
from app.paypal import SimulatedPayPal
from app.service import Service


def make():
    pp = SimulatedPayPal()
    svc = Service(db.connect(":memory:"), pp, pp.merchant_email)
    pid_a = svc.propose(sample_extract(SAMPLE_CONTRACT), SAMPLE_CONTRACT, "fixture")["project_id"]
    svc.approve(pid_a, "t")
    ms = svc.view(pid_a)["milestones"]
    svc.draft_invoice(ms[0]["id"], "t")
    svc.send_invoice(ms[0]["id"], "t", True)
    pid_b = svc.propose(sample_extract(SAMPLE_CONTRACT), SAMPLE_CONTRACT, "fixture")["project_id"]
    return svc, pp, pid_a, pid_b


def test_portfolio_brief_totals_and_actions():
    svc, _, pid_a, pid_b = make()
    brief = svc.portfolio_brief()
    assert brief["project_count"] == 2
    assert brief["outstanding_total"] == "3000.00"
    assert brief["collected_total"] == "0.00"
    assert brief["overdue_count"] == 0
    assert brief["actions"][0]["project_id"] == pid_b
    assert brief["actions"][0]["action"] == "Approve the plan"
    assert any(a["project_id"] == pid_a and a["action"] == "Follow up on payment" for a in brief["actions"])


def test_portfolio_brief_marks_overdue():
    svc, _, pid_a, _ = make()
    svc.c.execute("UPDATE milestones SET due_date='2000-01-01' WHERE project_id=? AND seq=1", (pid_a,))
    brief = svc.portfolio_brief()
    assert brief["overdue_count"] >= 1
    row = next(a for a in brief["actions"] if a["project_id"] == pid_a)
    assert row["overdue"] is True


def test_portfolio_brief_counts_paid():
    svc, pp, pid_a, _ = make()
    m = svc.view(pid_a)["milestones"][0]
    pp.simulate_payment(m["invoice_id"], "400.00")
    svc.handle_webhook(
        {"paypal-transmission-sig": pp.SIM_SIG},
        json.dumps({"id": "E1", "event_type": "INVOICING.INVOICE.PAID",
                    "resource": {"invoice": {"id": m["invoice_id"]}}}).encode(),
    )
    brief = svc.portfolio_brief()
    assert brief["collected_total"] == "400.00"
    assert brief["outstanding_total"] == "2600.00"
