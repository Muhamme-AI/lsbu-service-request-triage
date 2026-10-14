import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import EDGE_CSV, SAMPLE_CSV


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_reports_ai_off_by_default(client, monkeypatch):
    monkeypatch.delenv("TRIAGE_AI_PROVIDER", raising=False)
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["ai_configured"] is False


def test_rules_endpoint_exposes_categories_and_templates(client):
    body = client.get("/api/rules").json()
    names = [c["name"] for c in body["rules"]["categorisation"]["categories"]]
    assert "Access & Permissions" in names
    assert "template" in body["acknowledgements"]


def test_sample_dataset_runs(client):
    body = client.get("/api/sample", params={"dataset": "sample", "as_of": "2026-10-08"}).json()
    assert body["summary"]["total"] == 10
    assert body["as_of"] == "2026-10-08"
    assert "Human review queue" in body["markdown"]["summary"]


def test_upload_csv_is_triaged(client):
    with EDGE_CSV.open("rb") as handle:
        response = client.post("/api/triage", params={"as_of": "2026-10-08"}, files={"file": ("edge.csv", handle, "text/csv")})
    assert response.status_code == 200
    body = response.json()
    assert body["input_file"] == "edge.csv"
    assert body["summary"]["total"] == 15 and body["summary"]["invalid"] == 7


def test_upload_without_summary_column_is_a_400(client):
    response = client.post("/api/triage", files={"file": ("bad.csv", b"Name,Email\nJo,jo@example.com\n", "text/csv")})
    assert response.status_code == 400
    assert "Request Summary" in response.json()["detail"]


def test_bad_as_of_is_a_422(client):
    response = client.get("/api/sample", params={"as_of": "next tuesday"})
    assert response.status_code == 422


def test_ai_acknowledgement_falls_back_when_not_configured(client, monkeypatch):
    monkeypatch.delenv("TRIAGE_AI_PROVIDER", raising=False)
    payload = {
        "request": {
            "request_id": "REQ-003",
            "submitted_date": "02/10/2026",
            "requester_role": "Lecturer",
            "request_type": "Reporting & Analytics",
            "request_summary": "Create a dashboard showing module engagement and outstanding interventions.",
            "priority": "Medium",
            "channel": "Teams",
            "status": "Assigned",
        },
        "as_of": "2026-10-08",
    }
    body = client.post("/api/acknowledgement/ai", json=payload).json()
    assert body["ai_available"] is False
    assert body["ack_source"] == "template"
    assert "REQ-003" in body["acknowledgement"]
    assert "not configured" in body["ai_note"]


def test_sample_file_is_the_one_supplied_with_the_test():
    assert SAMPLE_CSV.read_text(encoding="utf-8-sig").startswith("Request ID,Submitted Date,Requester Role")
