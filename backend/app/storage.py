from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, List

from .config import PROJECTS_DIR


def project_dir(project_id: int) -> Path:
    path = PROJECTS_DIR / f"project_{project_id}"
    path.mkdir(parents=True, exist_ok=True)
    (path / "artifacts").mkdir(exist_ok=True)
    (path / "runs").mkdir(exist_ok=True)
    return path


def artifacts_dir(project_id: int) -> Path:
    path = project_dir(project_id) / "artifacts"
    path.mkdir(exist_ok=True)
    return path


def list_artifacts(project_id: int) -> List[str]:
    base = artifacts_dir(project_id)
    return [str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()]


def checksum_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()
