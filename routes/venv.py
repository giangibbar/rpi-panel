import subprocess
import shutil
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

VENVS_BASE = Path.home()


@router.get("/")
async def list_venvs():
    """Find all venvs under home directory with metadata."""
    venvs = []
    for pyvenv in VENVS_BASE.rglob("pyvenv.cfg"):
        venv_path = pyvenv.parent
        # Python version
        version = ""
        python_bin = venv_path / "bin" / "python3"
        if python_bin.exists():
            r = subprocess.run([str(python_bin), "--version"], capture_output=True, text=True)
            version = r.stdout.strip().replace("Python ", "")
        # Disk size
        try:
            size_bytes = sum(f.stat().st_size for f in venv_path.rglob("*") if f.is_file())
            size_mb = round(size_bytes / 1048576, 1)
        except Exception:
            size_mb = 0
        # Package count
        r = subprocess.run([str(venv_path / "bin" / "pip"), "list", "--format=json"], capture_output=True, text=True)
        import json
        try:
            pkg_count = len(json.loads(r.stdout))
        except Exception:
            pkg_count = 0
        venvs.append({"path": str(venv_path), "name": venv_path.name, "project": str(venv_path.parent.name), "version": version, "size_mb": size_mb, "pkg_count": pkg_count})
    return venvs


class CreateVenv(BaseModel):
    path: str


@router.post("/create")
async def create_venv(body: CreateVenv):
    r = subprocess.run(["python3", "-m", "venv", body.path], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}


class DeleteVenv(BaseModel):
    path: str


@router.post("/delete")
async def delete_venv(body: DeleteVenv):
    p = Path(body.path)
    if not p.exists() or not (p / "pyvenv.cfg").exists():
        return {"ok": False, "error": "Not a valid venv"}
    shutil.rmtree(p)
    return {"ok": True}


@router.get("/packages")
async def list_packages(venv_path: str):
    pip = Path(venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "list", "--format=json"], capture_output=True, text=True)
    import json
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


@router.get("/outdated")
async def outdated_packages(venv_path: str):
    pip = Path(venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "list", "--outdated", "--format=json"], capture_output=True, text=True, timeout=60)
    import json
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


class PipAction(BaseModel):
    venv_path: str
    package: str = ""


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


@router.post("/upgrade")
async def upgrade_package(body: PipAction):
    pip = Path(body.venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "install", "--upgrade", body.package], capture_output=True, text=True, timeout=120)
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}


class FreezeAction(BaseModel):
    venv_path: str


@router.get("/freeze")
async def freeze(venv_path: str):
    pip = Path(venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "freeze"], capture_output=True, text=True)
    return {"requirements": r.stdout}


@router.post("/install-requirements")
async def install_requirements(body: FreezeAction):
    req_file = Path(body.venv_path).parent / "requirements.txt"
    if not req_file.exists():
        return {"ok": False, "error": "No requirements.txt found in project"}
    pip = Path(body.venv_path) / "bin" / "pip"
    r = subprocess.run([str(pip), "install", "-r", str(req_file)], capture_output=True, text=True, timeout=120)
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}


class RunScript(BaseModel):
    venv_path: str
    script_path: str


@router.post("/run")
async def run_script(body: RunScript):
    python = Path(body.venv_path) / "bin" / "python3"
    r = subprocess.run([str(python), body.script_path], capture_output=True, text=True, timeout=60, cwd=str(Path(body.script_path).parent))
    return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}


class RunCode(BaseModel):
    venv_path: str
    code: str


@router.post("/run-code")
async def run_code(body: RunCode):
    python = Path(body.venv_path) / "bin" / "python3"
    r = subprocess.run([str(python), "-c", body.code], capture_output=True, text=True, timeout=30)
    return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr}
