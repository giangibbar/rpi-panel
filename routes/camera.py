import subprocess
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

SNAP_PATH = Path("/tmp/rpi-snapshot.jpg")


@router.get("/snapshot")
async def snapshot():
    """Take a snapshot using libcamera or return error if no camera."""
    r = subprocess.run(
        ["libcamera-still", "-o", str(SNAP_PATH), "--width", "1280", "--height", "720",
         "--nopreview", "-t", "1000"],
        capture_output=True, text=True, timeout=10
    )
    if r.returncode == 0 and SNAP_PATH.exists():
        return FileResponse(SNAP_PATH, media_type="image/jpeg")
    return {"error": "No camera available or capture failed", "details": r.stderr.strip()}


@router.get("/status")
async def camera_status():
    """Check if camera is available."""
    r = subprocess.run(["libcamera-hello", "--list-cameras"], capture_output=True, text=True, timeout=5)
    available = "Available cameras" in r.stdout and "No cameras" not in r.stdout
    return {"available": available, "info": r.stdout.strip()}
