from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import paramiko
from sqlmodel import Session

from .models import AuditLog, Execution, ExecutionPlan
from .storage import artifacts_dir, checksum_files

DENYLIST = ["rm -rf", "curl | sh", "mkfs", "dd if="]


class ExecutionProvider:
    def plan(self, commands: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def run_approved(self, plan: ExecutionPlan, session: Session) -> Execution:
        raise NotImplementedError


class LocalRunner(ExecutionProvider):
    def plan(self, commands: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        warnings = [cmd for cmd in commands if any(bad in cmd for bad in DENYLIST)]
        return {"commands": commands, "warnings": warnings, "context": context}

    def run_approved(self, plan: ExecutionPlan, session: Session) -> Execution:
        project_artifacts = artifacts_dir(plan.project_id)
        stdout_path = project_artifacts / f"exec_{plan.id}_stdout.log"
        stderr_path = project_artifacts / f"exec_{plan.id}_stderr.log"
        execution = Execution(
            project_id=plan.project_id,
            plan_id=plan.id,
            runner=plan.runner,
            status="running",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)
        commands = json.loads(plan.commands_json)
        combined_exit = 0
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_file:
            for command in commands:
                audit = AuditLog(
                    project_id=plan.project_id,
                    execution_id=execution.id,
                    command=command,
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                )
                session.add(audit)
                session.commit()
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=project_artifacts,
                    stdout=stdout_file,
                    stderr=stderr_file,
                )
                audit.artifact_checksum = checksum_files(
                    [Path(stdout_path), Path(stderr_path)]
                )
                audit.exit_code = result.returncode
                session.add(audit)
                session.commit()
                if result.returncode != 0:
                    combined_exit = result.returncode
                    break
        execution.status = "completed" if combined_exit == 0 else "failed"
        execution.exit_code = combined_exit
        execution.updated_at = datetime.utcnow()
        session.add(execution)
        session.commit()
        return execution


class SSHRunner(ExecutionProvider):
    def __init__(self, profile: Dict[str, Any]) -> None:
        self.profile = profile

    def plan(self, commands: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        warnings = [cmd for cmd in commands if any(bad in cmd for bad in DENYLIST)]
        return {"commands": commands, "warnings": warnings, "context": context}

    def run_approved(self, plan: ExecutionPlan, session: Session) -> Execution:
        project_artifacts = artifacts_dir(plan.project_id)
        stdout_path = project_artifacts / f"exec_{plan.id}_stdout.log"
        stderr_path = project_artifacts / f"exec_{plan.id}_stderr.log"
        execution = Execution(
            project_id=plan.project_id,
            plan_id=plan.id,
            runner=plan.runner,
            status="running",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )
        session.add(execution)
        session.commit()
        session.refresh(execution)
        commands = json.loads(plan.commands_json)
        hostname = self.profile["host"]
        username = self.profile["username"]
        key_path = self.profile.get("key_path")
        remote_dir = self.profile.get("remote_base_dir", ".")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, username=username, key_filename=key_path)
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_file:
            for command in commands:
                audit = AuditLog(
                    project_id=plan.project_id,
                    execution_id=execution.id,
                    command=command,
                    stdout_path=str(stdout_path),
                    stderr_path=str(stderr_path),
                )
                session.add(audit)
                session.commit()
                full_command = f"cd {remote_dir} && {command}"
                _, stdout, stderr = client.exec_command(full_command)
                stdout_text = stdout.read().decode("utf-8")
                stderr_text = stderr.read().decode("utf-8")
                stdout_file.write(stdout_text)
                stderr_file.write(stderr_text)
                exit_code = stdout.channel.recv_exit_status()
                audit.artifact_checksum = checksum_files(
                    [Path(stdout_path), Path(stderr_path)]
                )
                audit.exit_code = exit_code
                session.add(audit)
                session.commit()
                if exit_code != 0:
                    execution.exit_code = exit_code
                    execution.status = "failed"
                    break
        if execution.status != "failed":
            execution.status = "completed"
            execution.exit_code = 0
        execution.updated_at = datetime.utcnow()
        session.add(execution)
        session.commit()
        client.close()
        return execution


class SlurmRunner(SSHRunner):
    def run_approved(self, plan: ExecutionPlan, session: Session) -> Execution:
        profile = self.profile
        commands = json.loads(plan.commands_json)
        sbatch_lines = ["#!/bin/bash"]
        defaults = profile.get("defaults", {})
        if defaults.get("partition"):
            sbatch_lines.append(f"#SBATCH -p {defaults['partition']}")
        if defaults.get("time"):
            sbatch_lines.append(f"#SBATCH -t {defaults['time']}")
        if defaults.get("mem"):
            sbatch_lines.append(f"#SBATCH --mem={defaults['mem']}")
        if defaults.get("cpus"):
            sbatch_lines.append(f"#SBATCH -c {defaults['cpus']}")
        if defaults.get("gres"):
            sbatch_lines.append(f"#SBATCH --gres={defaults['gres']}")
        env_init = profile.get("env_init_commands", [])
        sbatch_lines.extend(env_init)
        sbatch_lines.extend(commands)
        script_content = "\n".join(sbatch_lines)
        plan.commands_json = json.dumps([script_content])
        return super().run_approved(plan, session)


RUNNER_REGISTRY = {
    "local": LocalRunner(),
}


def get_runner(runner: str, profile: Dict[str, Any]) -> ExecutionProvider:
    if runner == "local":
        return RUNNER_REGISTRY["local"]
    if runner == "ssh":
        return SSHRunner(profile)
    if runner == "slurm":
        return SlurmRunner(profile)
    raise ValueError(f"Unknown runner: {runner}")
