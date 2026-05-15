import subprocess
from fastapi import APIRouter

router = APIRouter()


@router.post("/reboot")
async def reboot():
    subprocess.Popen(["sudo", "reboot"])
    return {"ok": True, "message": "Rebooting..."}


@router.post("/shutdown")
async def shutdown():
    subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    return {"ok": True, "message": "Shutting down..."}
