import importlib

import pytest
from fastapi.testclient import TestClient

from app.extraction import SAMPLE_CONTRACT

TOKEN = {"X-MP-Token": "tok"}


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("MP_MODE", "sample")
    monkeypatch.setenv("LLM_PROVIDER", "sample")
    monkeypatch.setenv("MP_DB", str(tmp_path / "api.db"))
    monkeypatch.setenv("MP_ADMIN_TOKEN", "tok")
    import app.main as M
    importlib.reload(M)
    return TestClient(M.app)


def create(api, text=SAMPLE_CONTRACT):
    r = api.post("/api/projects", json={"text": text}, headers=TOKEN)
    assert r.status_code == 200, r.text
    return r.json()["project_id"]


def test_info_is_public(api):
    r = api.get("/api/info")
    assert r.status_code == 200
    assert r.json()["mode"] == "sample"


def test_project_routes_require_token(api):
    pid = create(api)
    assert api.get("/api/projects").status_code == 401
    assert api.get(f"/api/projects/{pid}").status_code == 401
    assert api.get("/api/brief").status_code == 401
    assert api.post(f"/api/projects/{pid}/approve", json={}).status_code == 401
    assert api.post(f"/api/projects/{pid}/risk").status_code == 401
    assert api.put(f"/api/projects/{pid}/plan", json={}).status_code == 401
    assert api.post(f"/api/projects/{pid}/risk", headers=TOKEN).status_code == 200


def test_create_and_read_project(api):
    pid = create(api)
    detail = api.get(f"/api/projects/{pid}", headers=TOKEN)
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "PROPOSED"
    assert len(body["milestones"]) == 3
    assert body["risk"] is None
    listing = api.get("/api/projects", headers=TOKEN).json()["projects"]
    assert listing[0]["id"] == pid


def test_approve_draft_send_flow(api):
    pid = create(api)
    assert api.post(f"/api/projects/{pid}/approve", json={}, headers=TOKEN).json()["status"] == "APPROVED"
    detail = api.get(f"/api/projects/{pid}", headers=TOKEN).json()
    first, second = detail["milestones"][0], detail["milestones"][1]
    assert api.post(f"/api/milestones/{first['id']}/draft", json={}, headers=TOKEN).status_code == 200
    sent = api.post(f"/api/milestones/{first['id']}/send", json={"confirm": True}, headers=TOKEN)
    assert sent.status_code == 200 and sent.json()["pay_link"]
    blocked = api.post(f"/api/milestones/{second['id']}/draft", json={}, headers=TOKEN)
    assert blocked.status_code == 409


def test_plan_edit_route(api):
    pid = create(api)
    p = api.get(f"/api/projects/{pid}", headers=TOKEN).json()
    body = {
        "client_name": p["client_name"], "client_email": p["client_email"], "total": p["total"],
        "currency": p["currency"],
        "milestones": [{"id": m["id"], "title": m["title"], "amount": m["amount"], "due_date": m["due_date"]}
                       for m in p["milestones"]],
    }
    body["milestones"][0]["amount"] = "abc"
    r = api.put(f"/api/projects/{pid}/plan", json=body, headers=TOKEN)
    assert r.status_code == 200
    assert r.json()["project"]["status"] == "BLOCKED"
    assert r.json()["errors"]


def test_risk_route_saves_verbatim_review(api):
    pid = create(api)
    r = api.post(f"/api/projects/{pid}/risk", headers=TOKEN)
    assert r.status_code == 200
    risks = r.json()["risk"]["risks"]
    assert len(risks) == 2
    assert all(note["evidence"] in SAMPLE_CONTRACT for note in risks)
    detail = api.get(f"/api/projects/{pid}", headers=TOKEN).json()
    assert detail["risk"]["risks"][0]["title"] == risks[0]["title"]


def test_brief_route(api):
    create(api)
    create(api)
    r = api.get("/api/brief", headers=TOKEN)
    assert r.status_code == 200
    body = r.json()
    assert body["project_count"] == 2
    assert body["outstanding_total"] == "3000.00"
    assert body["actions"][0]["action"] == "Approve the plan"


def test_webhook_size_cap(api):
    r = api.post("/api/webhooks/paypal", content=b"x" * (64 * 1024 + 1))
    assert r.status_code == 413


def test_simulate_payment_route(api):
    pid = create(api)
    api.post(f"/api/projects/{pid}/approve", json={}, headers=TOKEN)
    m = api.get(f"/api/projects/{pid}", headers=TOKEN).json()["milestones"][0]
    api.post(f"/api/milestones/{m['id']}/draft", json={}, headers=TOKEN)
    api.post(f"/api/milestones/{m['id']}/send", json={"confirm": True}, headers=TOKEN)
    r = api.post(f"/api/simulate/pay/{m['id']}", headers=TOKEN)
    assert r.status_code == 200
    assert r.json()["outcome"] == "milestone_paid"
    detail = api.get(f"/api/projects/{pid}", headers=TOKEN).json()
    assert detail["milestones"][0]["status"] == "PAID"
