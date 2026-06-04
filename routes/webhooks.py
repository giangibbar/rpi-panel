"""Webhooks: receive GitHub/external webhooks and trigger actions."""

import hashlib
import hmac
import json
import subprocess
import time
from pathlib import Path
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

HOOKS_FILE = Path(__file__).parent.parent / "webhooks_config.json"
HOOKS_LOG = Path(__file__).parent.parent / "webhooks_log.json"


def load_hooks() -> list:
    if HOOKS_FILE.exists():
        return json.loads(HOOKS_FILE.read_text())
    return [
        {"id": "deploy-web-terminal", "repo": "giangibbar/rpi-panel", "action": "/home/egamgia/SCRIPTS/deploy.sh web-terminal", "secret": "", "enabled": True},
        {"id": "deploy-risiko", "repo": "giangibbar/RISIKO", "action": "/home/egamgia/SCRIPTS/deploy.sh risiko", "secret": "", "enabled": True},
        {"id": "deploy-aifun", "repo": "giangibbar/aifun", "action": "/home/egamgia/SCRIPTS/deploy.sh aifun", "secret": "", "enabled": True},
        {"id": "deploy-fantai", "repo": "giangibbar/FantAI", "action": "/home/egamgia/SCRIPTS/deploy.sh fantai", "secret": "", "enabled": True},
    ]


def save_hooks(hooks: list):
    HOOKS_FILE.write_text(json.dumps(hooks, indent=2))


def log_event(hook_id: str, repo: str, event: str, status: str, output: str = ""):
    logs = []
    if HOOKS_LOG.exists():
        try:
            logs = json.loads(HOOKS_LOG.read_text())
        except Exception:
            pass
    logs.append({"ts": int(time.time()), "hook_id": hook_id, "repo": repo, "event": event, "status": status, "output": output[:500]})
    # Keep last 50
    HOOKS_LOG.write_text(json.dumps(logs[-50:], indent=2))


@router.post("/github")
async def github_webhook(request: Request):
    """Receive GitHub webhook (push events) and trigger deploy."""
    body = await request.body()
    event = request.headers.get("X-GitHub-Event", "")
    
    try:
        payload = json.loads(body)
    except Exception:
        return {"error": "Invalid JSON"}

    repo = payload.get("repository", {}).get("full_name", "")
    hooks = load_hooks()

    for hook in hooks:
        if not hook["enabled"] or hook["repo"] != repo:
            continue
        # Verify secret if configured
        if hook["secret"]:
            sig = request.headers.get("X-Hub-Signature-256", "")
            expected = "sha256=" + hmac.new(hook["secret"].encode(), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                log_event(hook["id"], repo, event, "rejected: bad signature")
                continue
        # Only trigger on push to default branch
        if event == "push":
            ref = payload.get("ref", "")
            branch = ref.split("/")[-1] if "/" in ref else ref
            # Execute action
            try:
                r = subprocess.run(hook["action"], shell=True, capture_output=True, text=True, timeout=120)
                status = "ok" if r.returncode == 0 else "failed"
                log_event(hook["id"], repo, event, status, r.stdout + r.stderr)
            except Exception as e:
                log_event(hook["id"], repo, event, f"error: {e}")
            return {"ok": True, "hook": hook["id"]}

    log_event("unknown", repo, event, "no matching hook")
    return {"ok": False, "error": "No matching hook"}


@router.get("/")
async def list_hooks():
    """List configured webhooks."""
    return load_hooks()


@router.get("/logs")
async def get_logs():
    """Get webhook event log."""
    if HOOKS_LOG.exists():
        return json.loads(HOOKS_LOG.read_text())
    return []


class HookConfig(BaseModel):
    id: str
    repo: str
    action: str
    secret: str = ""
    enabled: bool = True


@router.post("/add")
async def add_hook(body: HookConfig):
    hooks = load_hooks()
    hooks = [h for h in hooks if h["id"] != body.id]
    hooks.append(body.model_dump())
    save_hooks(hooks)
    return {"ok": True}


class RemoveHook(BaseModel):
    id: str


@router.post("/remove")
async def remove_hook(body: RemoveHook):
    hooks = [h for h in load_hooks() if h["id"] != body.id]
    save_hooks(hooks)
    return {"ok": True}
