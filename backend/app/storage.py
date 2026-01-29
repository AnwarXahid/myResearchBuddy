from pathlib import Path

from .config import PROJECTS_DIR


def project_dir(project_id: int) -> Path:
    path = PROJECTS_DIR / f"project_{project_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def stage_dir(project_id: int, stage_id: str) -> Path:
    path = project_dir(project_id) / stage_id
    path.mkdir(parents=True, exist_ok=True)
    return path
