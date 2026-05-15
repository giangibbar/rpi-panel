import subprocess
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

SSH_DIR = Path.home() / ".ssh"
AUTH_KEYS = SSH_DIR / "authorized_keys"


@router.get("/")
async def list_keys():
    """List authorized SSH keys."""
    if not AUTH_KEYS.exists():
        return {"keys": []}
    keys = []
    for i, line in enumerate(AUTH_KEYS.read_text().strip().split("\n")):
        if line.strip():
            parts = line.split()
            keys.append({
                "id": i,
                "type": parts[0] if parts else "",
                "comment": parts[2] if len(parts) > 2 else "",
                "fingerprint": _fingerprint(line),
            })
    return {"keys": keys}


def _fingerprint(key_line: str) -> str:
    r = subprocess.run(["ssh-keygen", "-lf", "-"], input=key_line, capture_output=True, text=True)
    return r.stdout.strip().split()[1] if r.returncode == 0 else ""


class AddKey(BaseModel):
    key: str  # full public key line


@router.post("/add")
async def add_key(body: AddKey):
    SSH_DIR.mkdir(mode=0o700, exist_ok=True)
    current = AUTH_KEYS.read_text() if AUTH_KEYS.exists() else ""
    if body.key.strip() in current:
        return {"ok": False, "error": "Key already exists"}
    with open(AUTH_KEYS, "a") as f:
        f.write(body.key.strip() + "\n")
    AUTH_KEYS.chmod(0o600)
    return {"ok": True}


class RemoveKey(BaseModel):
    id: int


@router.post("/remove")
async def remove_key(body: RemoveKey):
    if not AUTH_KEYS.exists():
        return {"ok": False, "error": "No keys file"}
    lines = AUTH_KEYS.read_text().strip().split("\n")
    if 0 <= body.id < len(lines):
        lines.pop(body.id)
        AUTH_KEYS.write_text("\n".join(lines) + "\n" if lines else "")
        return {"ok": True}
    return {"ok": False, "error": "Invalid key ID"}


@router.get("/host-key")
async def host_key():
    """Get the host's public key (for adding to other machines)."""
    pub = Path("/etc/ssh/ssh_host_ed25519_key.pub")
    if pub.exists():
        return {"key": pub.read_text().strip()}
    return {"key": ""}
