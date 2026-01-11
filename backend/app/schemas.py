from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class ProjectRead(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    settings: Dict[str, Any]


class StepRunRequest(BaseModel):
    provider: str = "gemini"
    model: str = "gemini-1.5-pro"
    temperature: float = 0.2
    max_tokens: int = 2048
    inputs: Dict[str, Any] = Field(default_factory=dict)


class StepRunResponse(BaseModel):
    run_id: int
    output: Dict[str, Any]
    prompt_version: str


class StepEditRequest(BaseModel):
    output: Dict[str, Any]
    notes: str = ""


class StepRunRead(BaseModel):
    id: int
    created_at: datetime
    prompt_version: str
    provider: str
    model: str
    temperature: float
    max_tokens: int
    input_json: Dict[str, Any]
    output_json: Dict[str, Any]
    notes: str


class StepDiffResponse(BaseModel):
    run_a: int
    run_b: int
    diff: List[str]


class ExecutionPlanRequest(BaseModel):
    runner: str
    commands: List[str]
    context: Dict[str, Any] = Field(default_factory=dict)


class ExecutionPlanResponse(BaseModel):
    plan_id: int
    runner: str
    commands: List[str]
    approved: bool
    warnings: List[str] = Field(default_factory=list)


class ExecutionRunRequest(BaseModel):
    plan_id: int


class ExecutionStatusResponse(BaseModel):
    execution_id: int
    status: str
    exit_code: Optional[int]


class ExecutionLogResponse(BaseModel):
    stdout: str
    stderr: str


class UploadResponse(BaseModel):
    stored: List[str]


class ArtifactListing(BaseModel):
    files: List[str]


class ExportResponse(BaseModel):
    path: str
    warning: Optional[str] = None
