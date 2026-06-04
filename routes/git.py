"""Git management: projects, status, diff, stash, discard, commit+push."""

import json
import subprocess
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

PROJECTS_FILE = Path(__file__).parent.parent / "git_projects.json"

# Default projects
DEFAULT_PROJECTS = [
    {"name": "web-terminal", "path": "/home/egamgia/WORKSPACE/web-terminal", "branch": "main"},
    {"name": "RISIKO", "path": "/home/egamgia/WORKSPACE/RISIKO", "branch": "master"},
    {"name": "AiFun", "path": "/home/egamgia/WORKSPACE/AiFun", "branch": "main"},
    {"name": "FantAI", "path": "/home/egamgia/WORKSPACE/FantAI", "branch": "main"},
]


def load_projects() -> list:
    if PROJECTS_FILE.exists():
        return json.loads(PROJECTS_FILE.read_text())
    return DEFAULT_PROJECTS


def save_projects(projects: list):
    PROJECTS_FILE.write_text(json.dumps(projects, indent=2))


def _run(cmd: list[str], cwd: str) -> tuple[str, int]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
    return (r.stdout + r.stderr).rstrip(), r.returncode


@router.get("/projects")
async def list_projects():
    """List all configured git projects with their status."""
    projects = load_projects()
    result = []
    for p in projects:
        path = p["path"]
        if not Path(path).exists():
            result.append({**p, "status": "missing"})
            continue
        out, _ = _run(["git", "status", "--porcelain"], path)
        changed = len([l for l in out.split("\n") if l.strip()]) if out else 0
        branch_out, _ = _run(["git", "branch", "--show-current"], path)
        result.append({**p, "changed_files": changed, "current_branch": branch_out.strip()})
    return result


@router.get("/status/{name}")
async def project_status(name: str):
    """Get detailed git status for a project."""
    projects = load_projects()
    proj = next((p for p in projects if p["name"] == name), None)
    if not proj:
        return {"error": "Project not found"}
    path = proj["path"]
    out, _ = _run(["git", "status", "--porcelain"], path)
    files = []
    for line in out.split("\n"):
        if not line:
            continue
        # Format: XY filename (first 2 chars = status, skip space at pos 2)
        filepath = line[3:] if len(line) > 3 else line
        status = line[:2].strip() or "?"
        files.append({"status": status, "file": filepath})
    return {"project": proj, "files": files}


@router.get("/diff/{name}/{filepath:path}")
async def file_diff(name: str, filepath: str):
    """Get diff for a specific file."""
    projects = load_projects()
    proj = next((p for p in projects if p["name"] == name), None)
    if not proj:
        return {"error": "Project not found"}
    path = proj["path"]
    # Try unstaged, then staged, then HEAD
    out, _ = _run(["git", "diff", "--", filepath], path)
    if not out:
        out, _ = _run(["git", "diff", "--cached", "--", filepath], path)
    if not out:
        out, _ = _run(["git", "diff", "HEAD", "--", filepath], path)
    if not out:
        # Untracked or binary — show file content
        fpath = Path(path) / filepath
        if fpath.exists():
            if fpath.stat().st_size > 50000:
                out = f"(file too large: {fpath.stat().st_size} bytes)"
            else:
                try:
                    out = f"+++ new file: {filepath}\n" + fpath.read_text(errors="replace")
                except Exception:
                    out = "(binary file)"
    return {"diff": out}


class StashRequest(BaseModel):
    name: str


@router.post("/stash")
async def stash(body: StashRequest):
    """Stash all changes in a project."""
    projects = load_projects()
    proj = next((p for p in projects if p["name"] == body.name), None)
    if not proj:
        return {"error": "Project not found"}
    out, code = _run(["git", "stash", "push", "-m", "web-terminal stash"], proj["path"])
    return {"ok": code == 0, "output": out}


class DiscardRequest(BaseModel):
    name: str
    file: str = ""  # empty = discard all


@router.post("/discard")
async def discard(body: DiscardRequest):
    """Discard changes (checkout file or clean)."""
    projects = load_projects()
    proj = next((p for p in projects if p["name"] == body.name), None)
    if not proj:
        return {"error": "Project not found"}
    if body.file:
        out, code = _run(["git", "checkout", "--", body.file], proj["path"])
        if code != 0:
            # Untracked file - remove it
            out, code = _run(["rm", "-f", body.file], proj["path"])
    else:
        _run(["git", "checkout", "--", "."], proj["path"])
        out, code = _run(["git", "clean", "-fd"], proj["path"])
    return {"ok": code == 0, "output": out}


class PushRequest(BaseModel):
    name: str
    message: str
    files: list[str] = []  # empty = all files


@router.post("/push")
async def commit_and_push(body: PushRequest):
    """Commit selected files (or all) and push."""
    projects = load_projects()
    proj = next((p for p in projects if p["name"] == body.name), None)
    if not proj:
        return {"error": "Project not found"}
    path = proj["path"]
    branch = proj["branch"]

    if body.files:
        for f in body.files:
            _run(["git", "add", "--", f], path)
    else:
        _run(["git", "add", "-A"], path)
    out, code = _run(["git", "commit", "-m", body.message], path)
    if code != 0:
        return {"ok": False, "output": out}
    out2, code2 = _run(["git", "push", "origin", branch], path)
    return {"ok": code2 == 0, "output": out + "\n" + out2}


class PullRequest(BaseModel):
    name: str


@router.post("/pull")
async def pull(body: PullRequest):
    """Pull latest changes and return what changed."""
    projects = load_projects()
    proj = next((p for p in projects if p["name"] == body.name), None)
    if not proj:
        return {"error": "Project not found"}
    path = proj["path"]
    branch = proj["branch"]

    # Get current HEAD before pull
    old_head, _ = _run(["git", "rev-parse", "HEAD"], path)
    out, code = _run(["git", "pull", "origin", branch], path)
    if code != 0:
        return {"ok": False, "output": out, "files": []}
    # Get changed files between old and new HEAD
    new_head, _ = _run(["git", "rev-parse", "HEAD"], path)
    files = []
    if old_head.strip() != new_head.strip():
        diff_out, _ = _run(["git", "diff", "--stat", old_head.strip(), new_head.strip()], path)
        for line in diff_out.split("\n"):
            line = line.strip()
            if "|" in line:
                fname = line.split("|")[0].strip()
                change = line.split("|")[1].strip()
                files.append({"file": fname, "change": change})
    return {"ok": True, "output": out, "files": files, "up_to_date": old_head.strip() == new_head.strip()}


class AddProjectRequest(BaseModel):
    name: str
    path: str
    branch: str = "main"


@router.post("/projects/add")
async def add_project(body: AddProjectRequest):
    """Add a new project to track."""
    projects = load_projects()
    if any(p["name"] == body.name for p in projects):
        return {"error": "Project already exists"}
    projects.append(body.model_dump())
    save_projects(projects)
    return {"ok": True}


class RemoveProjectRequest(BaseModel):
    name: str


@router.post("/projects/remove")
async def remove_project(body: RemoveProjectRequest):
    """Remove a project from tracking."""
    projects = [p for p in load_projects() if p["name"] != body.name]
    save_projects(projects)
    return {"ok": True}
