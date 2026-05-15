import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


@router.get("/")
async def list_users():
    users = []
    with open("/etc/passwd") as f:
        for line in f:
            parts = line.strip().split(":")
            uid = int(parts[2])
            if uid >= 1000 and parts[6] != "/usr/sbin/nologin":
                users.append({"name": parts[0], "uid": uid, "home": parts[5], "shell": parts[6]})
    return users


class ChangePassword(BaseModel):
    username: str
    password: str


@router.post("/password")
async def change_password(body: ChangePassword):
    r = subprocess.run(["sudo", "chpasswd"], input=f"{body.username}:{body.password}", capture_output=True, text=True)
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}


class CreateUser(BaseModel):
    username: str
    password: str


@router.post("/create")
async def create_user(body: CreateUser):
    r = subprocess.run(["sudo", "useradd", "-m", "-s", "/bin/bash", body.username], capture_output=True, text=True)
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr.strip()}
    subprocess.run(["sudo", "chpasswd"], input=f"{body.username}:{body.password}", capture_output=True, text=True)
    return {"ok": True}
