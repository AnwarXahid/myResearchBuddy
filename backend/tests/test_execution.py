from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db

client = TestClient(app)


def test_execution_requires_approval():
    init_db()
    project = client.post("/api/projects", json={"name": "Test", "description": ""}).json()
    plan = client.post(
        f"/api/projects/{project['id']}/executions/plan",
        json={"runner": "local", "commands": ["echo ok"], "context": {}},
    ).json()
    resp = client.post(
        f"/api/projects/{project['id']}/executions/run",
        json={"plan_id": plan["plan_id"]},
    )
    assert resp.status_code == 400
