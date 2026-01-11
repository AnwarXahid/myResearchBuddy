from pathlib import Path
import json

from backend.app.database import init_db
from backend.app.models import Project, StepRun, StepState
from backend.app.database import engine
from sqlmodel import Session

init_db()

with Session(engine) as session:
    project = Project(name="Demo Project", description="Example research pipeline project")
    session.add(project)
    session.commit()
    session.refresh(project)

    part1_output = {
        "polished_problem_statement": "Demo problem statement.",
        "contribution_hypotheses": ["H1", "H2", "H3"],
        "paper_type_decision": "Empirical study",
        "related_work_candidates": [],
        "risks_and_unknowns": ["Risk A"]
    }
    run = StepRun(
        project_id=project.id,
        step_id="part1",
        prompt_version="demo",
        provider="demo",
        model="demo",
        temperature=0.2,
        max_tokens=512,
        input_json=json.dumps({"idea": "demo"}),
        output_json=json.dumps(part1_output),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    state = StepState(project_id=project.id, step_id="part1", current_run_id=run.id, locked=True)
    session.add(state)
    session.commit()

    project_dir = Path("data/projects") / f"project_{project.id}" / "artifacts"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "metrics.json").write_text(json.dumps({"accuracy": 0.9}), encoding="utf-8")
    (project_dir / "results_summary.md").write_text("Demo results summary.", encoding="utf-8")

print("Demo project created.")
