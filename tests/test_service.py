"""HTTP service tests."""

from fastapi.testclient import TestClient

from service.app import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_upload(sample_db):
    client = TestClient(app)
    with sample_db.open("rb") as handle:
        response = client.post(
            "/analyze/upload",
            files={"database": ("sample.db", handle, "application/octet-stream")},
            data={"carve": "true"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert payload["summary"]["live_records"] >= 2
