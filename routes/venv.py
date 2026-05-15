import subprocess
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

VENVS_BASE = Path.home()


@router.get("/")
async def list_venvs():
    """Find all venvs under home directory."""
    venvs = []
    for pyvenv in VENVS_BASE.rglob("pyvenv.cfg"):
        venv_path = pyvenv.parent
        venvs.append({"path": str(venv_path), "name": venv_path.name, "project": str(venv_path.parent.name)})
    return venvs


class CreateVenv(BaseModel):
    path: str  # full path where to create venv


@router.post("/create")
async def create_venv(body: CreateVenv):
    r = subprocess.run(["python3", "-m", "venv", body.path], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}


class PipAction(BaseModel):
    venv_path: str
    package: str = ""


@router.get("/packages")
async def list_packages(venv_path: str):
    pip = Path(venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "list", "--format=json"], capture_output=True, text=True)
    import json
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


@router.post("/install")
async def install_package(body: PipAction):
    pip = Path(body.venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "install", body.package], capture_output=True, text=True, timeout=120)
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}


@router.post("/uninstall")
async def uninstall_package(body: PipAction):
    pip = Path(body.venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "uninstall", "-y", body.package], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}
