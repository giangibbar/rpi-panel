"""Execute shell commands — sync and async (fire-and-forget) modes."""

import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Store for async jobs
_jobs: dict[str, dict] = {}


class ExecRequest(BaseModel):
    command: str
    timeout: int = 30
    async_mode: bool = False
    cwd: Optional[str] = None


@router.post("")
async def exec_command(req: ExecRequest, session: str = Cookie(default="")):
    from main import check_auth
    if not check_auth(session):
        raise HTTPException(401)

    if req.async_mode:
        job_id = uuid.uuid4().hex[:8]
        _jobs[job_id] = {"status": "running", "stdout": "", "stderr": "", "exit_code": None}
        asyncio.create_task(_run_async(job_id, req.command, req.timeout, req.cwd))
        return {"job_id": job_id}

    proc = await asyncio.create_subprocess_shell(
        req.command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=req.cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=req.timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"stdout": "", "stderr": "timeout", "exit_code": -1}

    return {
        "stdout": stdout.decode(errors="replace"),
        "stderr": stderr.decode(errors="replace"),
        "exit_code": proc.returncode,
    }


@router.get("/{job_id}")
async def get_job(job_id: str, session: str = Cookie(default="")):
    from main import check_auth
    if not check_auth(session):
        raise HTTPException(401)
    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")
    return _jobs[job_id]


async def _run_async(job_id: str, command: str, timeout: int, cwd: Optional[str]):
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        _jobs[job_id] = {
            "status": "done",
            "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"),
            "exit_code": proc.returncode,
        }
    except asyncio.TimeoutError:
        proc.kill()
        _jobs[job_id] = {"status": "timeout", "stdout": "", "stderr": "timeout", "exit_code": -1}
