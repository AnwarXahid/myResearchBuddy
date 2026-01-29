from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db

client = TestClient(app)


def test_step_locking():
    init_db()
    project = client.post("/api/projects", json={"name": "Workflow", "description": ""}).json()
    # edit manual output
    edit = client.post(
        f"/api/projects/{project['id']}/steps/part1/edit",
        json={"output": {"polished_problem_statement": "x", "contribution_hypotheses": [], "paper_type_decision": "", "related_work_candidates": [], "risks_and_unknowns": []}},
    )
    assert edit.status_code == 200
    approve = client.post(f"/api/projects/{project['id']}/steps/part1/approve")
    assert approve.status_code == 200
    locked_edit = client.post(
        f"/api/projects/{project['id']}/steps/part1/edit",
        json={"output": {"polished_problem_statement": "y", "contribution_hypotheses": [], "paper_type_decision": "", "related_work_candidates": [], "risks_and_unknowns": []}},
    )
    assert locked_edit.status_code == 400
    unlock = client.post(f"/api/projects/{project['id']}/steps/part1/unlock")
    assert unlock.status_code == 200
