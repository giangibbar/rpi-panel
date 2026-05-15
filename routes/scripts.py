import subprocess
import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
SCRIPTS_DIR.mkdir(exist_ok=True)


@router.get("/")
async def list_scripts():
    scripts = []
    for f in sorted(SCRIPTS_DIR.glob("*.json")):
        meta = json.loads(f.read_text())
        scripts.append({"id": f.stem, "name": meta["name"], "description": meta.get("description", "")})
    return scripts


class Script(BaseModel):
    name: str
    description: str = ""
    content: str


@router.post("/save")
async def save_script(body: Script):
    slug = body.name.lower().replace(" ", "-").replace("/", "")[:50]
    meta = {"name": body.name, "description": body.description, "content": body.content}
    (SCRIPTS_DIR / f"{slug}.json").write_text(json.dumps(meta, indent=2))
    return {"ok": True, "id": slug}


@router.get("/get/{script_id}")
async def get_script(script_id: str):
    f = SCRIPTS_DIR / f"{script_id}.json"
    if not f.exists():
        return {"error": "Not found"}
    return json.loads(f.read_text())


@router.post("/run/{script_id}")
async def run_script(script_id: str):
    f = SCRIPTS_DIR / f"{script_id}.json"
    if not f.exists():
        return {"error": "Not found"}
    meta = json.loads(f.read_text())
    try:
        r = subprocess.run(
            ["bash", "-c", meta["content"]],
            capture_output=True, text=True, timeout=60
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr, "code": r.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout (60s)"}


@router.post("/delete/{script_id}")
async def delete_script(script_id: str):
    f = SCRIPTS_DIR / f"{script_id}.json"
    if f.exists():
        f.unlink()
    return {"ok": True}
