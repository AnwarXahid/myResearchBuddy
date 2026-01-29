from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from .database import get_session, init_db
from .models import Project, Stage, StageFile
from .schemas import ProjectCreate, ProjectDetail, ProjectRead, StageRead, StageFileRead
from .storage import stage_dir

STAGES = [
    "idea",
    "related_work",
    "method",
    "experiments",
    "results",
    "draft",
    "submission",
]

app = FastAPI(title="Research Progress Tracker")

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
def health_check():
    return {"status": "ok"}


@app.post("/api/projects", response_model=ProjectRead)
def create_project(payload: ProjectCreate, session: Session = Depends(get_session)):
    project = Project(name=payload.name, description=payload.description)
    session.add(project)
    session.commit()
    session.refresh(project)
    for stage_id in STAGES:
        session.add(Stage(project_id=project.id, stage_id=stage_id))
    session.commit()
    return ProjectRead(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
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
        )
        for project in projects
    ]


@app.get("/api/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    stages = session.exec(select(Stage).where(Stage.project_id == project_id)).all()
    files = session.exec(select(StageFile).where(StageFile.project_id == project_id)).all()
    return ProjectDetail(
        project=ProjectRead(
            id=project.id,
            name=project.name,
            description=project.description,
            created_at=project.created_at,
        ),
        stages=[
            StageRead(
                stage_id=stage.stage_id,
                completed=stage.completed,
                completed_at=stage.completed_at,
            )
            for stage in stages
        ],
        files=[
            StageFileRead(
                id=file.id,
                filename=file.filename,
                stored_path=file.stored_path,
                uploaded_at=file.uploaded_at,
            )
            for file in files
        ],
    )


@app.post("/api/projects/{project_id}/stages/{stage_id}/complete")
def complete_stage(project_id: int, stage_id: str, session: Session = Depends(get_session)):
    stage = session.exec(
        select(Stage).where(Stage.project_id == project_id, Stage.stage_id == stage_id)
    ).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    stage.completed = True
    stage.completed_at = datetime.utcnow()
    session.add(stage)
    session.commit()
    return {"status": "completed", "stage_id": stage_id}


@app.post("/api/projects/{project_id}/stages/{stage_id}/reset")
def reset_stage(project_id: int, stage_id: str, session: Session = Depends(get_session)):
    stage = session.exec(
        select(Stage).where(Stage.project_id == project_id, Stage.stage_id == stage_id)
    ).first()
    if not stage:
        raise HTTPException(status_code=404, detail="Stage not found")
    stage.completed = False
    stage.completed_at = None
    session.add(stage)
    session.commit()
    return {"status": "reset", "stage_id": stage_id}


@app.post("/api/projects/{project_id}/stages/{stage_id}/upload")
def upload_stage_file(
    project_id: int,
    stage_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    if stage_id not in STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")
    if not file.filename:
        raise HTTPException(status_code=400, detail="File required")
    dest_dir = stage_dir(project_id, stage_id)
    dest_path = dest_dir / file.filename
    dest_path.write_bytes(file.file.read())
    stage_file = StageFile(
        project_id=project_id,
        stage_id=stage_id,
        filename=file.filename,
        stored_path=str(dest_path),
    )
    session.add(stage_file)
    session.commit()
    session.refresh(stage_file)
    return {"file_id": stage_file.id, "stored_path": stage_file.stored_path}


@app.get("/api/projects/{project_id}/stages/{stage_id}/files", response_model=List[StageFileRead])
def list_stage_files(project_id: int, stage_id: str, session: Session = Depends(get_session)):
    files = session.exec(
        select(StageFile).where(StageFile.project_id == project_id, StageFile.stage_id == stage_id)
    ).all()
    return [
        StageFileRead(
            id=file.id,
            filename=file.filename,
            stored_path=file.stored_path,
            uploaded_at=file.uploaded_at,
        )
        for file in files
    ]


@app.get("/api/files/{file_id}")
def download_file(file_id: int, session: Session = Depends(get_session)):
    file = session.get(StageFile, file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file.stored_path, filename=file.filename)
