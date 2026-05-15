import subprocess
import time
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

BACKUP_DIR = Path.home() / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


@router.get("/")
async def list_backups():
    backups = []
    for f in sorted(BACKUP_DIR.glob("*.tar.gz"), reverse=True):
        backups.append({
            "name": f.name,
            "size_mb": round(f.stat().st_size / 1048576, 1),
            "created": f.stat().st_mtime,
        })
    return backups


class BackupRequest(BaseModel):
    paths: list[str] = ["/home/egamgia"]
    name: str = ""


@router.post("/create")
async def create_backup(body: BackupRequest):
    name = body.name or f"backup-{time.strftime('%Y%m%d-%H%M%S')}"
    dest = BACKUP_DIR / f"{name}.tar.gz"
    try:
        r = subprocess.run(
            ["tar", "czf", str(dest)] + body.paths,
            capture_output=True, text=True, timeout=300
        )
        if dest.exists():
            return {"ok": True, "name": dest.name, "size_mb": round(dest.stat().st_size / 1048576, 1)}
        return {"ok": False, "error": r.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout (5 min)"}


class RestoreRequest(BaseModel):
    name: str
    dest: str = "/"


@router.post("/restore")
async def restore_backup(body: RestoreRequest):
    src = BACKUP_DIR / body.name
    if not src.exists():
        return {"ok": False, "error": "Backup not found"}
    r = subprocess.run(
        ["sudo", "tar", "xzf", str(src), "-C", body.dest],
        capture_output=True, text=True, timeout=300
    )
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}


class DeleteBackup(BaseModel):
    name: str


@router.post("/delete")
async def delete_backup(body: DeleteBackup):
    f = BACKUP_DIR / body.name
    if f.exists() and f.suffix == ".gz":
        f.unlink()
        return {"ok": True}
    return {"ok": False, "error": "Not found"}
