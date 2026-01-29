from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Stage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    stage_id: str = Field(index=True)
    completed: bool = False
    completed_at: Optional[datetime] = None


class StageFile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    stage_id: str = Field(index=True)
    filename: str
    stored_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
