from __future__ import annotations

import json
import subprocess
import time
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

    def cancel(self, execution: Execution, plan: ExecutionPlan, session: Session) -> Execution:
        execution.status = "cancelled"
        execution.updated_at = datetime.utcnow()
        session.add(execution)
        session.commit()
        return execution

    def collect_artifacts(self, plan: ExecutionPlan, execution: Execution) -> List[str]:
        return []


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
        context = json.loads(plan.context_json) if plan.context_json else {}
        commands = json.loads(plan.commands_json)
        hostname = self.profile["host"]
        username = self.profile["username"]
        key_path = self.profile.get("key_path")
        remote_dir = self.profile.get("remote_base_dir", ".")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname,
            username=username,
            key_filename=key_path,
            port=self.profile.get("port", 22),
        )
        sftp = client.open_sftp()
        self._stage_uploads(
            plan.project_id,
            sftp,
            context.get("staging", {}).get("upload", []),
            remote_dir,
        )
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
        sftp.close()
        client.close()
        return execution

    def collect_artifacts(self, plan: ExecutionPlan, execution: Execution) -> List[str]:
        context = json.loads(plan.context_json) if plan.context_json else {}
        downloads = context.get("staging", {}).get("download", [])
        if not downloads:
            return []
        hostname = self.profile["host"]
        username = self.profile["username"]
        key_path = self.profile.get("key_path")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname,
            username=username,
            key_filename=key_path,
            port=self.profile.get("port", 22),
        )
        sftp = client.open_sftp()
        base = artifacts_dir(plan.project_id)
        saved = []
        for item in downloads:
            remote_path = item.get("remote")
            local_rel = item.get("local")
            if not remote_path or not local_rel:
                continue
            local_path = base / local_rel
            local_path.parent.mkdir(parents=True, exist_ok=True)
            sftp.get(remote_path, str(local_path))
            saved.append(str(local_path.relative_to(base)))
        sftp.close()
        client.close()
        return saved

    def _stage_uploads(
        self,
        project_id: int,
        sftp: paramiko.SFTPClient,
        uploads: List[Dict[str, Any]],
        remote_dir: str,
    ) -> None:
        for item in uploads:
            local_path = item.get("local")
            remote_path = item.get("remote")
            if not local_path or not remote_path:
                continue
            local = Path(local_path)
            if not local.is_absolute():
                local = artifacts_dir(project_id) / local_path
            if not remote_path.startswith("/"):
                remote_path = f"{remote_dir}/{remote_path}"
            sftp.put(str(local), remote_path)


class SlurmRunner(SSHRunner):
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
        context = json.loads(plan.context_json) if plan.context_json else {}
        commands = json.loads(plan.commands_json)
        hostname = self.profile["host"]
        username = self.profile["username"]
        key_path = self.profile.get("key_path")
        remote_dir = self.profile.get("remote_base_dir", ".")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname,
            username=username,
            key_filename=key_path,
            port=self.profile.get("port", 22),
        )
        sftp = client.open_sftp()
        self._stage_uploads(
            plan.project_id,
            sftp,
            context.get("staging", {}).get("upload", []),
            remote_dir,
        )
        sbatch_lines = ["#!/bin/bash"]
        defaults = self.profile.get("defaults", {})
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
        env_init = self.profile.get("env_init_commands", [])
        sbatch_lines.extend(env_init)
        sbatch_lines.extend(commands)
        script_content = "\n".join(sbatch_lines)
        remote_script = f"{remote_dir}/rps_{plan.id}.sbatch"
        with sftp.file(remote_script, "w") as remote_file:
            remote_file.write(script_content)
        audit = AuditLog(
            project_id=plan.project_id,
            execution_id=execution.id,
            command=f"sbatch {remote_script}",
            stdout_path=str(stdout_path),
            stderr_path=str(stderr_path),
        )
        session.add(audit)
        session.commit()
        _, stdout, stderr = client.exec_command(f"cd {remote_dir} && sbatch {remote_script}")
        stdout_text = stdout.read().decode("utf-8")
        stderr_text = stderr.read().decode("utf-8")
        job_id = stdout_text.strip().split()[-1] if stdout_text else ""
        if job_id:
            context["slurm_job_id"] = job_id
            plan.context_json = json.dumps(context)
            session.add(plan)
            session.commit()
        with stdout_path.open("w", encoding="utf-8") as stdout_file:
            stdout_file.write(stdout_text)
        with stderr_path.open("w", encoding="utf-8") as stderr_file:
            stderr_file.write(stderr_text)
        audit.exit_code = stdout.channel.recv_exit_status()
        audit.artifact_checksum = checksum_files([stdout_path, stderr_path])
        session.add(audit)
        session.commit()
        status = self._poll_job(client, job_id)
        execution.exit_code = 0 if status == "COMPLETED" else 1
        execution.status = "completed" if status == "COMPLETED" else "failed"
        execution.updated_at = datetime.utcnow()
        session.add(execution)
        session.commit()
        slurm_output = f"{remote_dir}/slurm-{job_id}.out"
        try:
            sftp.get(slurm_output, str(project_artifacts / f"slurm_{job_id}.out"))
        except FileNotFoundError:
            pass
        sftp.close()
        client.close()
        return execution

    def cancel(self, execution: Execution, plan: ExecutionPlan, session: Session) -> Execution:
        context = json.loads(plan.context_json) if plan.context_json else {}
        job_id = context.get("slurm_job_id")
        if not job_id:
            return super().cancel(execution, plan, session)
        hostname = self.profile["host"]
        username = self.profile["username"]
        key_path = self.profile.get("key_path")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname,
            username=username,
            key_filename=key_path,
            port=self.profile.get("port", 22),
        )
        client.exec_command(f"scancel {job_id}")
        client.close()
        execution.status = "cancelled"
        execution.updated_at = datetime.utcnow()
        session.add(execution)
        session.commit()
        return execution

    def _poll_job(self, client: paramiko.SSHClient, job_id: str) -> str:
        if not job_id:
            return "FAILED"
        for _ in range(30):
            _, stdout, _ = client.exec_command(f"squeue -h -j {job_id}")
            if not stdout.read().decode("utf-8").strip():
                break
            time.sleep(2)
        _, stdout, _ = client.exec_command(f"sacct -j {job_id} --format=State --noheader")
        state = stdout.read().decode("utf-8").strip().split()[0] if stdout else "FAILED"
        return state


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
