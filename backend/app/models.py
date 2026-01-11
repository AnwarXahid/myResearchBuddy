from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    settings_json: str = "{}"


class StepState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    step_id: str = Field(index=True)
    locked: bool = False
    current_run_id: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StepRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    step_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    prompt_version: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    input_json: str
    output_json: str
    notes: str = ""


class ExecutionPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    runner: str
    commands_json: str
    context_json: str = "{}"
    approved: bool = False
    approved_at: Optional[datetime] = None


class Execution(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    plan_id: int
    runner: str
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    exit_code: Optional[int] = None
    stdout_path: str = ""
    stderr_path: str = ""


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    execution_id: Optional[int] = None
    command: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    exit_code: Optional[int] = None
    stdout_path: str = ""
    stderr_path: str = ""
    artifact_checksum: str = ""
