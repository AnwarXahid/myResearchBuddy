from __future__ import annotations

import difflib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from sqlmodel import Session, select

from .config import PROJECTS_DIR
from .database import get_session, init_db
from .execution import get_runner
from .ingestion import ingest_metrics
from .models import AuditLog, Execution, ExecutionPlan, Project, StepRun, StepState
from .schemas import (
    ArtifactListing,
    ExecutionLogResponse,
    ExecutionPlanRequest,
    ExecutionPlanResponse,
    ExecutionRunRequest,
    ExecutionStatusResponse,
    ExportResponse,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    StepDiffResponse,
    StepEditRequest,
    StepRunRead,
    StepRunRequest,
    StepRunResponse,
    UploadResponse,
)
from .storage import artifacts_dir, list_artifacts
from .workflow import STEP_IDS, run_step

app = FastAPI(title="Research Pipeline Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, session: Session = Depends(get_session)):
    project = Project(
        name=payload.name,
        description=payload.description,
        settings_json=json.dumps({"include_unverified_citations": False}),
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        settings=json.loads(project.settings_json),
    )


@app.get("/api/projects", response_model=List[ProjectRead])
def list_projects(session: Session = Depends(get_session)):
    projects = session.exec(select(Project)).all()
    return [
        ProjectRead(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
            updated_at=project.updated_at,
            settings=json.loads(project.settings_json),
        )
        for project in projects
    ]


@app.get("/api/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        settings=json.loads(project.settings_json),
    )


@app.patch("/api/projects/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int, payload: ProjectUpdate, session: Session = Depends(get_session)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.settings is not None:
        project.settings_json = json.dumps(payload.settings)
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        settings=json.loads(project.settings_json),
    )


@app.patch("/api/projects/{project_id}/settings", response_model=ProjectRead)
def update_project_settings(
    project_id: int, payload: ProjectUpdate, session: Session = Depends(get_session)
):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if payload.settings is None:
        raise HTTPException(status_code=400, detail="Settings payload required")
    project.settings_json = json.dumps(payload.settings)
    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        settings=json.loads(project.settings_json),
    )


@app.post("/api/projects/{project_id}/steps/{step_id}/run", response_model=StepRunResponse)
def run_project_step(
    project_id: int,
    step_id: str,
    payload: StepRunRequest,
    session: Session = Depends(get_session),
):
    if step_id not in STEP_IDS:
        raise HTTPException(status_code=400, detail="Unknown step")
    state = session.exec(
        select(StepState).where(
            StepState.project_id == project_id, StepState.step_id == step_id
        )
    ).first()
    if state and state.locked:
        raise HTTPException(status_code=400, detail="Step is locked")
    project = session.get(Project, project_id)
    project_settings = json.loads(project.settings_json) if project else {}
    citations = []
    if step_id == "final":
        part1_run = session.exec(
            select(StepRun)
            .where(StepRun.project_id == project_id, StepRun.step_id == "part1")
            .order_by(StepRun.created_at.desc())
        ).first()
        if part1_run:
            citations = json.loads(part1_run.output_json).get("related_work_candidates", [])
    run = run_step(
        project_id=project_id,
        step_id=step_id,
        inputs=payload.inputs,
        provider=payload.provider,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        project_settings=project_settings,
        citations=citations,
    )
    step_run = StepRun(
        project_id=project_id,
        step_id=step_id,
        prompt_version=run["prompt_version"],
        provider=payload.provider,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        input_json=json.dumps(payload.inputs),
        output_json=json.dumps(run["output"]),
    )
    session.add(step_run)
    session.commit()
    session.refresh(step_run)
    if not state:
        state = StepState(project_id=project_id, step_id=step_id, current_run_id=step_run.id)
    else:
        state.current_run_id = step_run.id
        state.updated_at = datetime.utcnow()
    session.add(state)
    session.commit()
    return StepRunResponse(run_id=step_run.id, output=run["output"], prompt_version=run["prompt_version"])


@app.post("/api/projects/{project_id}/steps/{step_id}/approve")
def approve_step(project_id: int, step_id: str, session: Session = Depends(get_session)):
    state = session.exec(
        select(StepState).where(
            StepState.project_id == project_id, StepState.step_id == step_id
        )
    ).first()
    if not state:
        raise HTTPException(status_code=404, detail="Step state not found")
    state.locked = True
    state.updated_at = datetime.utcnow()
    session.add(state)
    session.commit()
    return {"status": "locked"}


@app.post("/api/projects/{project_id}/steps/{step_id}/unlock")
def unlock_step(project_id: int, step_id: str, session: Session = Depends(get_session)):
    state = session.exec(
        select(StepState).where(
            StepState.project_id == project_id, StepState.step_id == step_id
        )
    ).first()
    if not state:
        raise HTTPException(status_code=404, detail="Step state not found")
    state.locked = False
    state.updated_at = datetime.utcnow()
    session.add(state)
    session.commit()
    return {"status": "unlocked"}


@app.post("/api/projects/{project_id}/steps/{step_id}/edit")
def edit_step(
    project_id: int,
    step_id: str,
    payload: StepEditRequest,
    session: Session = Depends(get_session),
):
    state = session.exec(
        select(StepState).where(
            StepState.project_id == project_id, StepState.step_id == step_id
        )
    ).first()
    if state and state.locked:
        raise HTTPException(status_code=400, detail="Step is locked")
    step_run = StepRun(
        project_id=project_id,
        step_id=step_id,
        prompt_version="manual",
        provider="manual",
        model="manual",
        temperature=0,
        max_tokens=0,
        input_json=json.dumps({}),
        output_json=json.dumps(payload.output),
        notes=payload.notes,
    )
    session.add(step_run)
    session.commit()
    session.refresh(step_run)
    if not state:
        state = StepState(project_id=project_id, step_id=step_id, current_run_id=step_run.id)
    else:
        state.current_run_id = step_run.id
        state.updated_at = datetime.utcnow()
    session.add(state)
    session.commit()
    return {"run_id": step_run.id}


@app.get("/api/projects/{project_id}/steps/{step_id}/runs", response_model=List[StepRunRead])
def list_step_runs(project_id: int, step_id: str, session: Session = Depends(get_session)):
    runs = session.exec(
        select(StepRun)
        .where(StepRun.project_id == project_id, StepRun.step_id == step_id)
        .order_by(StepRun.created_at.desc())
    ).all()
    return [
        StepRunRead(
            id=run.id,
            created_at=run.created_at,
            prompt_version=run.prompt_version,
            provider=run.provider,
            model=run.model,
            temperature=run.temperature,
            max_tokens=run.max_tokens,
            input_json=json.loads(run.input_json),
            output_json=json.loads(run.output_json),
            notes=run.notes,
        )
        for run in runs
    ]


@app.get("/api/projects/{project_id}/steps/{step_id}/diff", response_model=StepDiffResponse)
def diff_step_runs(
    project_id: int,
    step_id: str,
    run_a: int,
    run_b: int,
    session: Session = Depends(get_session),
):
    run_a_obj = session.get(StepRun, run_a)
    run_b_obj = session.get(StepRun, run_b)
    if not run_a_obj or not run_b_obj:
        raise HTTPException(status_code=404, detail="Run not found")
    text_a = json.dumps(json.loads(run_a_obj.output_json), indent=2, sort_keys=True).splitlines()
    text_b = json.dumps(json.loads(run_b_obj.output_json), indent=2, sort_keys=True).splitlines()
    diff = list(difflib.unified_diff(text_a, text_b, fromfile=str(run_a), tofile=str(run_b)))
    return StepDiffResponse(run_a=run_a, run_b=run_b, diff=diff)


@app.post("/api/projects/{project_id}/upload", response_model=UploadResponse)
def upload_artifacts(
    project_id: int,
    files: List[UploadFile] = File(...),
):
    dest_dir = artifacts_dir(project_id)
    stored = []
    for uploaded in files:
        dest_path = dest_dir / uploaded.filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(uploaded.file.read())
        stored.append(str(dest_path.relative_to(dest_dir)))
    return UploadResponse(stored=stored)


@app.post("/api/projects/{project_id}/ingest")
def ingest_project_metrics(
    project_id: int,
    file: UploadFile = File(...),
    label: str | None = Form(default=None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="File required")
    try:
        paths = ingest_metrics(project_id, file.filename, file.file.read(), label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"artifacts": paths}


@app.get("/api/projects/{project_id}/artifacts", response_model=ArtifactListing)
def list_project_artifacts(project_id: int):
    return ArtifactListing(files=list_artifacts(project_id))


@app.get("/api/projects/{project_id}/artifacts/content")
def read_artifact_content(project_id: int, path: str):
    base = artifacts_dir(project_id).resolve()
    target = (base / path).resolve()
    if base not in target.parents and target != base:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return PlainTextResponse(target.read_text(encoding="utf-8"))


@app.get("/api/projects/{project_id}/artifacts/file")
def read_artifact_file(project_id: int, path: str):
    base = artifacts_dir(project_id).resolve()
    target = (base / path).resolve()
    if base not in target.parents and target != base:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(str(target))


@app.get("/api/projects/{project_id}/export/latex", response_model=ExportResponse)
def export_latex(project_id: int):
    project_path = PROJECTS_DIR / f"project_{project_id}" / "artifacts"
    latex_dir = project_path / "latex"
    latex_dir.mkdir(parents=True, exist_ok=True)
    main_tex = latex_dir / "main.tex"
    if not main_tex.exists():
        main_tex.write_text("% TODO: generate LaTeX content", encoding="utf-8")
    return ExportResponse(path=str(main_tex))


@app.get("/api/projects/{project_id}/export/pdf", response_model=ExportResponse)
def export_pdf(project_id: int):
    project_path = PROJECTS_DIR / f"project_{project_id}" / "artifacts" / "latex"
    pdf_path = project_path / "main.pdf"
    if pdf_path.exists():
        return ExportResponse(path=str(pdf_path))
    main_tex = project_path / "main.tex"
    if not main_tex.exists():
        main_tex.write_text("% TODO: generate LaTeX content", encoding="utf-8")
    from shutil import which

    if which("latexmk") is None:
        return ExportResponse(path=str(main_tex), warning="LaTeX not installed")
    import subprocess

    subprocess.run(["latexmk", "-pdf", "main.tex"], cwd=project_path, check=False)
    if pdf_path.exists():
        return ExportResponse(path=str(pdf_path))
    return ExportResponse(path=str(main_tex), warning="PDF generation failed")


@app.post("/api/projects/{project_id}/executions/plan", response_model=ExecutionPlanResponse)
def plan_execution(
    project_id: int,
    payload: ExecutionPlanRequest,
    session: Session = Depends(get_session),
):
    profile = payload.context.get("cluster_profile", {})
    runner = get_runner(payload.runner, profile)
    plan_data = runner.plan(payload.commands, payload.context)
    plan = ExecutionPlan(
        project_id=project_id,
        runner=payload.runner,
        commands_json=json.dumps(payload.commands),
        context_json=json.dumps(payload.context),
        approved=False,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return ExecutionPlanResponse(
        plan_id=plan.id,
        runner=plan.runner,
        commands=plan_data["commands"],
        approved=plan.approved,
        warnings=plan_data.get("warnings", []),
    )


@app.post("/api/projects/{project_id}/executions/run", response_model=ExecutionStatusResponse)
def run_execution(
    project_id: int,
    payload: ExecutionRunRequest,
    session: Session = Depends(get_session),
):
    plan = session.get(ExecutionPlan, payload.plan_id)
    if not plan or plan.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    if not plan.approved:
        raise HTTPException(status_code=400, detail="Plan not approved")
    context = json.loads(plan.context_json)
    profile = context.get("cluster_profile", {})
    runner = get_runner(plan.runner, profile)
    execution = runner.run_approved(plan, session)
    return ExecutionStatusResponse(
        execution_id=execution.id, status=execution.status, exit_code=execution.exit_code
    )


@app.post("/api/projects/{project_id}/executions/plan/{plan_id}/approve")
def approve_execution_plan(
    project_id: int,
    plan_id: int,
    session: Session = Depends(get_session),
):
    plan = session.get(ExecutionPlan, plan_id)
    if not plan or plan.project_id != project_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.approved = True
    plan.approved_at = datetime.utcnow()
    session.add(plan)
    session.commit()
    return {"status": "approved"}


@app.get("/api/projects/{project_id}/executions/{execution_id}/logs", response_model=ExecutionLogResponse)
def execution_logs(
    project_id: int,
    execution_id: int,
    session: Session = Depends(get_session),
):
    execution = session.get(Execution, execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    stdout = Path(execution.stdout_path).read_text(encoding="utf-8") if execution.stdout_path else ""
    stderr = Path(execution.stderr_path).read_text(encoding="utf-8") if execution.stderr_path else ""
    return ExecutionLogResponse(stdout=stdout, stderr=stderr)


@app.get("/api/projects/{project_id}/executions/{execution_id}/status", response_model=ExecutionStatusResponse)
def execution_status(
    project_id: int,
    execution_id: int,
    session: Session = Depends(get_session),
):
    execution = session.get(Execution, execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ExecutionStatusResponse(
        execution_id=execution.id,
        status=execution.status,
        exit_code=execution.exit_code,
    )


@app.post("/api/projects/{project_id}/executions/{execution_id}/cancel")
def cancel_execution(project_id: int, execution_id: int, session: Session = Depends(get_session)):
    execution = session.get(Execution, execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    plan = session.get(ExecutionPlan, execution.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    context = json.loads(plan.context_json) if plan.context_json else {}
    runner = get_runner(plan.runner, context.get("cluster_profile", {}))
    runner.cancel(execution, plan, session)
    return {"status": execution.status, "execution_id": execution.id}


@app.post("/api/projects/{project_id}/executions/{execution_id}/collect")
def collect_execution_artifacts(
    project_id: int, execution_id: int, session: Session = Depends(get_session)
):
    execution = session.get(Execution, execution_id)
    if not execution or execution.project_id != project_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    plan = session.get(ExecutionPlan, execution.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    context = json.loads(plan.context_json) if plan.context_json else {}
    runner = get_runner(plan.runner, context.get("cluster_profile", {}))
    files = runner.collect_artifacts(plan, execution)
    return {"status": "collected", "files": files}
