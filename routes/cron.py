import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


@router.get("/")
async def list_crons():
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if r.returncode != 0:
        return {"jobs": []}
    jobs = []
    for i, line in enumerate(r.stdout.strip().split("\n")):
        if line.strip() and not line.startswith("#"):
            parts = line.split(None, 5)
            if len(parts) >= 6:
                jobs.append({
                    "id": i,
                    "minute": parts[0],
                    "hour": parts[1],
                    "day": parts[2],
                    "month": parts[3],
                    "weekday": parts[4],
                    "command": parts[5],
                    "raw": line,
                })
    return {"jobs": jobs}


class CronJob(BaseModel):
    schedule: str  # "*/5 * * * *"
    command: str


@router.post("/create")
async def create_cron(body: CronJob):
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    current = r.stdout if r.returncode == 0 else ""
    new_line = f"{body.schedule} {body.command}\n"
    new_crontab = current.rstrip("\n") + "\n" + new_line
    p = subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)
    return {"ok": p.returncode == 0, "error": p.stderr.strip()}


class CronDelete(BaseModel):
    line_index: int


@router.post("/delete")
async def delete_cron(body: CronDelete):
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if r.returncode != 0:
        return {"ok": False, "error": "No crontab"}
    lines = r.stdout.strip().split("\n")
    if 0 <= body.line_index < len(lines):
        lines.pop(body.line_index)
    new_crontab = "\n".join(lines) + "\n"
    p = subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)
    return {"ok": p.returncode == 0, "error": p.stderr.strip()}


class CronEdit(BaseModel):
    line_index: int
    schedule: str
    command: str


@router.post("/edit")
async def edit_cron(body: CronEdit):
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if r.returncode != 0:
        return {"ok": False, "error": "No crontab"}
    lines = r.stdout.strip().split("\n")
    if 0 <= body.line_index < len(lines):
        lines[body.line_index] = f"{body.schedule} {body.command}"
    new_crontab = "\n".join(lines) + "\n"
    p = subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True)
    return {"ok": p.returncode == 0, "error": p.stderr.strip()}
