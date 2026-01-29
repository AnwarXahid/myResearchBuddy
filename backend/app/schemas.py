from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectRead(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime


class StageRead(BaseModel):
    stage_id: str
    completed: bool
    completed_at: Optional[datetime]


class StageFileRead(BaseModel):
    id: int
    filename: str
    stored_path: str
    uploaded_at: datetime


class ProjectDetail(BaseModel):
    project: ProjectRead
    stages: List[StageRead]
    files: List[StageFileRead]
