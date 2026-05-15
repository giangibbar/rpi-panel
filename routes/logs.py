import subprocess
from fastapi import APIRouter

router = APIRouter()


@router.get("/auth")
async def auth_logs(lines: int = 50):
    r = subprocess.run(["sudo", "journalctl", "-u", "ssh", "--no-pager", "-n", str(lines), "--output=short"], capture_output=True, text=True)
    return {"logs": r.stdout}


@router.get("/failed")
async def failed_logins():
    r = subprocess.run(["sudo", "journalctl", "-u", "ssh", "--no-pager", "-n", "200", "--output=short"], capture_output=True, text=True)
    failed = [l for l in r.stdout.split("\n") if "Failed" in l or "Invalid" in l]
    return {"count": len(failed), "entries": failed[-50:]}


@router.get("/fail2ban")
async def fail2ban_status():
    r = subprocess.run(["sudo", "fail2ban-client", "status", "sshd"], capture_output=True, text=True)
    if r.returncode != 0:
        return {"installed": False}
    return {"installed": True, "status": r.stdout.strip()}
