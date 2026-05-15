import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


@router.get("/upgradable")
async def upgradable():
    subprocess.run(["sudo", "apt", "update", "-qq"], capture_output=True)
    r = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True)
    pkgs = []
    for line in r.stdout.strip().split("\n")[1:]:
        if "/" in line:
            name = line.split("/")[0]
            pkgs.append(name)
    return {"packages": pkgs, "count": len(pkgs)}


@router.post("/update")
async def update():
    r = subprocess.run(
        ["sudo", "apt", "upgrade", "-y", "-qq"],
        capture_output=True, text=True, timeout=300
    )
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}


class PkgAction(BaseModel):
    name: str


@router.post("/install")
async def install(body: PkgAction):
    r = subprocess.run(
        ["sudo", "apt", "install", "-y", "-qq", body.name],
        capture_output=True, text=True, timeout=120
    )
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}


@router.post("/remove")
async def remove(body: PkgAction):
    r = subprocess.run(
        ["sudo", "apt", "remove", "-y", "-qq", body.name],
        capture_output=True, text=True, timeout=60
    )
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}
