import json
import pytest
from fastapi.testclient import TestClient
from app import main

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_billing_ticket_and_draft(client):
    response = client.post("/tickets", json={"ticket_id": "T-101", "message": "I was charged twice for my monthly invoice."})
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "Billing"
    assert body["priority"] == "High"
    assert body["assigned_team"] == "Finance Support"
    assert "draft" in body["draft_response"].lower()
    assert body["message_sent"] is False


def test_duplicate_ticket_id_is_rejected(client):
    payload = {"ticket_id": "T-102", "message": "The application crashes during upload."}
    assert client.post("/tickets", json=payload).status_code == 201
    response = client.post("/tickets", json=payload)
    assert response.status_code == 409


def test_invalid_ticket_input_is_rejected(client):
    response = client.post("/tickets", json={"ticket_id": "!!", "message": "bad"})
    assert response.status_code == 422


def test_ambiguous_message_is_routed_for_review(client):
    response = client.post("/tickets", json={"ticket_id": "T-103", "message": "I need help with my account issue."})
    assert response.status_code == 201
    body = response.json()
    assert body["needs_review"] is True
    assert body["status"] == "needs_review"


def test_approval_changes_status_and_creates_audit(client):
    client.post("/tickets", json={"ticket_id": "T-104", "message": "The app crashes with an error during upload."})
    response = client.post("/tickets/T-104/approve", json={"reviewer": "supervisor-1", "note": "Checked the draft"})
    assert response.status_code == 200
    assert response.json()["ticket"]["status"] == "draft_ready"
    assert response.json()["message_sent"] is False
    audit = client.get("/tickets/T-104/audit").json()
    assert [event["action"] for event in audit["events"]] == ["created", "approved"]


def test_approval_unknown_ticket_returns_404(client):
    assert client.post("/tickets/MISSING/approve", json={"reviewer": "supervisor"}).status_code == 404


def test_repeated_approval_is_rejected(client):
    client.post("/tickets", json={"ticket_id": "T-105", "message": "Please send me the billing invoice."})
    approval = {"reviewer": "supervisor"}
    assert client.post("/tickets/T-105/approve", json=approval).status_code == 200
    assert client.post("/tickets/T-105/approve", json=approval).status_code == 409


def test_holdout_dataset_has_ten_cases_and_evaluation_endpoint(client):
    data = json.loads((main.APP_DIR.parent / "sample_data" / "tickets.json").read_text())
    assert len([item for item in data if item["split"] == "test"]) == 10
    result = client.get("/evaluation")
    assert result.status_code == 200
    assert result.json()["test_count"] == 10
    assert 0 <= result.json()["accuracy"] <= 1


def test_missing_ticket_returns_404(client):
    assert client.get("/tickets/not-there").status_code == 404


def test_urgent_priority_and_required_output_fields(client):
    response = client.post("/tickets", json={
        "ticket_id": "T-106",
        "message": "The production server is down for all users and urgent help is needed.",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "Technical"
    assert body["priority"] == "Urgent"
    assert body["assigned_team"] == "Technical Support"
    assert body["summary"]
    assert body["draft_response"]
    assert body["status"] in {"needs_review", "pending_approval"}


def test_approval_does_not_send_a_message(client):
    client.post("/tickets", json={"ticket_id": "T-107", "message": "Please send me the billing invoice copy."})
    response = client.post("/tickets/T-107/approve", json={"reviewer": "supervisor-2"})
    assert response.status_code == 200
    assert response.json()["message_sent"] is False


def test_frozen_holdout_accuracy_is_reproducible(client):
    result = client.get("/evaluation").json()
    assert result["test_count"] == 10
    assert result["correct"] == 10
    assert result["accuracy"] == 1.0
    assert all(row["correct"] for row in result["results"])
