import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


@router.get("/status")
async def status():
    r = subprocess.run(["sudo", "ufw", "status", "numbered"], capture_output=True, text=True)
    lines = r.stdout.strip().split("\n")
    active = "active" in (lines[0] if lines else "")
    rules = []
    for line in lines[3:]:
        if line.strip():
            rules.append(line.strip())
    return {"active": active, "rules": rules, "raw": r.stdout}


@router.post("/enable")
async def enable():
    r = subprocess.run(["sudo", "ufw", "--force", "enable"], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "output": r.stdout.strip()}


@router.post("/disable")
async def disable():
    r = subprocess.run(["sudo", "ufw", "disable"], capture_output=True, text=True)
    return {"ok": r.returncode == 0}


class AddRule(BaseModel):
    rule: str  # e.g. "allow 80/tcp" or "allow from 192.168.1.0/24"


@router.post("/add")
async def add_rule(body: AddRule):
    parts = ["sudo", "ufw"] + body.rule.split()
    r = subprocess.run(parts, capture_output=True, text=True)
    return {"ok": r.returncode == 0, "output": r.stdout.strip() + r.stderr.strip()}


class DeleteRule(BaseModel):
    number: int


@router.post("/delete")
async def delete_rule(body: DeleteRule):
    r = subprocess.run(["sudo", "ufw", "--force", "delete", str(body.number)], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "output": r.stdout.strip()}
