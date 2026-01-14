from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db

client = TestClient(app)


def test_final_results_blocked_without_metrics():
    init_db()
    project = client.post("/api/projects", json={"name": "Gate", "description": ""}).json()
    resp = client.post(
        f"/api/projects/{project['id']}/steps/final/run",
        json={
            "provider": "gemini",
            "model": "gemini-1.5-pro",
            "temperature": 0.2,
            "max_tokens": 64,
            "inputs": {},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["output"]["results_allowed"] is False
    assert "metrics.json" in data["output"]["reason"]
