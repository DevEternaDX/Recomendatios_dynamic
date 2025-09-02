from datetime import date

from fastapi.testclient import TestClient

from backend.app import app


def test_simulate_endpoint_minimal():
    client = TestClient(app)
    payload = {"user_id": "demo_user", "date": str(date.today())}
    resp = client.post("/simulate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "count" in body


