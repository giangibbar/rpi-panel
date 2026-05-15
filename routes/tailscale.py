import subprocess
from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
async def status():
    """Check Tailscale status."""
    r = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True)
    if r.returncode != 0:
        return {"installed": False, "error": "Tailscale not installed or not running"}
    import json
    try:
        return {"installed": True, "status": json.loads(r.stdout)}
    except Exception:
        return {"installed": True, "raw": r.stdout}


@router.get("/ip")
async def get_ip():
    """Get Tailscale IP."""
    r = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True)
    if r.returncode == 0:
        return {"ip": r.stdout.strip()}
    return {"ip": None, "error": "Not connected"}


@router.post("/up")
async def up():
    r = subprocess.run(["sudo", "tailscale", "up"], capture_output=True, text=True, timeout=30)
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}


@router.post("/down")
async def down():
    r = subprocess.run(["sudo", "tailscale", "down"], capture_output=True, text=True)
    return {"ok": r.returncode == 0}


@router.get("/install-instructions")
async def install_instructions():
    return {"steps": [
        "curl -fsSL https://tailscale.com/install.sh | sh",
        "sudo tailscale up",
        "Authenticate in browser with the link provided",
        "Access your Pi from anywhere via Tailscale IP",
    ]}
