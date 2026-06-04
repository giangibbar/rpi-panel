"""Photo management: list RAF files from USB, generate previews, transfer."""

import os
import subprocess
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()

USB_MOUNT = "/media/usb"
DCIM_PATH = f"{USB_MOUNT}/DCIM"
IMAGES_DIR = "/home/egamgia/IMAGES"
CACHE_DIR = "/tmp/raf-thumbs"


@router.get("/status")
async def usb_status():
    """Check if USB is mounted and return photo count."""
    mounted = os.path.ismount(USB_MOUNT)
    photos = []
    if mounted:
        photos = _list_photos()
    return {"mounted": mounted, "photo_count": len(photos)}


@router.get("/list")
async def list_photos():
    """List all RAF/JPG photos on USB."""
    if not os.path.ismount(USB_MOUNT):
        raise HTTPException(404, "USB not mounted")
    return {"photos": _list_photos()}


@router.get("/thumb/{filename}")
async def get_thumbnail(filename: str):
    """Generate and return JPEG thumbnail for a RAF file."""
    photo_path = _find_photo(filename)
    if not photo_path:
        raise HTTPException(404, "Photo not found")

    os.makedirs(CACHE_DIR, exist_ok=True)
    thumb_path = f"{CACHE_DIR}/{filename}.jpg"

    if not os.path.exists(thumb_path):
        # Extract embedded JPEG from RAF (fast, no full decode)
        r = subprocess.run(
            ["dcraw", "-e", "-c", str(photo_path)],
            capture_output=True, timeout=30
        )
        if r.returncode != 0 or not r.stdout:
            # Fallback: half-size decode
            r = subprocess.run(
                ["dcraw", "-c", "-h", "-w", str(photo_path)],
                capture_output=True, timeout=60
            )
            if r.returncode != 0:
                raise HTTPException(500, "Failed to decode RAF")
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(r.stdout))
            img.thumbnail((800, 800))
            img.save(thumb_path, "JPEG", quality=80)
        else:
            with open(thumb_path, "wb") as f:
                f.write(r.stdout)

    return Response(
        content=Path(thumb_path).read_bytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"}
    )


@router.get("/preview/{filename}")
async def get_preview(filename: str):
    """Return larger preview JPEG."""
    photo_path = _find_photo(filename)
    if not photo_path:
        raise HTTPException(404, "Photo not found")

    os.makedirs(CACHE_DIR, exist_ok=True)
    preview_path = f"{CACHE_DIR}/{filename}_preview.jpg"

    if not os.path.exists(preview_path):
        # Extract embedded JPEG (full size from camera)
        r = subprocess.run(
            ["dcraw", "-e", "-c", str(photo_path)],
            capture_output=True, timeout=30
        )
        if r.returncode == 0 and r.stdout:
            with open(preview_path, "wb") as f:
                f.write(r.stdout)
        else:
            raise HTTPException(500, "Failed to extract preview")

    return Response(
        content=Path(preview_path).read_bytes(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"}
    )


class TransferRequest(BaseModel):
    files: list[str]
    destination: str  # "images" or "downloads"


@router.post("/transfer")
async def transfer_photos(req: TransferRequest):
    """Copy selected photos to destination."""
    if req.destination == "images":
        dest = IMAGES_DIR
    elif req.destination == "downloads":
        dest = IMAGES_DIR  # always copy to RPi, download via browser separately
    else:
        raise HTTPException(400, "Invalid destination")

    os.makedirs(dest, exist_ok=True)
    copied, errors = [], []
    for filename in req.files:
        src = _find_photo(filename)
        if src:
            try:
                shutil.copy2(str(src), os.path.join(dest, filename))
                copied.append(filename)
            except Exception as e:
                errors.append({"file": filename, "error": str(e)})
        else:
            errors.append({"file": filename, "error": "not found"})

    return {"copied": len(copied), "errors": errors}


@router.get("/download/{filename}")
async def download_photo(filename: str):
    """Download a RAF file directly."""
    photo_path = _find_photo(filename)
    if not photo_path:
        raise HTTPException(404, "Photo not found")
    return Response(
        content=photo_path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/mount")
async def mount_usb():
    """Mount USB drive."""
    if os.path.ismount(USB_MOUNT):
        return {"status": "already_mounted"}
    r = subprocess.run(["sudo", "mount", "/dev/sda1", USB_MOUNT], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise HTTPException(500, f"Mount failed: {r.stderr}")
    return {"status": "mounted"}


@router.post("/eject")
async def eject_usb():
    """Safely unmount USB drive."""
    if not os.path.ismount(USB_MOUNT):
        return {"status": "not_mounted"}
    # Clear thumbnail cache
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR, ignore_errors=True)
    r = subprocess.run(["sudo", "umount", USB_MOUNT], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise HTTPException(500, f"Eject failed: {r.stderr}")
    return {"status": "ejected"}


def _list_photos() -> list[dict]:
    """Scan DCIM folders for RAF/JPG files."""
    photos = []
    if not os.path.exists(DCIM_PATH):
        return photos
    for folder in sorted(Path(DCIM_PATH).iterdir()):
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.suffix.upper() in (".RAF", ".JPG", ".JPEG"):
                stat = f.stat()
                photos.append({
                    "name": f.name,
                    "folder": folder.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
    return photos


def _find_photo(filename: str) -> Path | None:
    """Find a photo by filename in DCIM subfolders."""
    if not os.path.exists(DCIM_PATH):
        return None
    for folder in Path(DCIM_PATH).iterdir():
        if folder.is_dir():
            path = folder / filename
            if path.exists():
                return path
    return None
