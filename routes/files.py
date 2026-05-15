import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter()


@router.get("/browse")
async def browse(path: str = "/home/egamgia"):
    p = Path(path).resolve()
    if not p.exists():
        return {"error": "Path not found"}
    items = []
    try:
        for entry in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                    "size": stat.st_size if entry.is_file() else 0,
                    "modified": stat.st_mtime,
                })
            except PermissionError:
                items.append({"name": entry.name, "path": str(entry), "is_dir": entry.is_dir(), "size": 0, "modified": 0})
    except PermissionError:
        return {"error": "Permission denied", "items": []}
    return {"path": str(p), "parent": str(p.parent), "items": items}


@router.get("/read")
async def read_file(path: str):
    p = Path(path)
    if not p.is_file():
        return {"error": "Not a file"}
    try:
        content = p.read_text(errors="replace")
        return {"path": str(p), "content": content}
    except Exception as e:
        return {"error": str(e)}


class WriteFile(BaseModel):
    path: str
    content: str


@router.post("/write")
async def write_file(body: WriteFile):
    try:
        Path(body.path).write_text(body.content)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class CreateItem(BaseModel):
    path: str
    is_dir: bool = False


@router.post("/create")
async def create_item(body: CreateItem):
    try:
        if body.is_dir:
            Path(body.path).mkdir(parents=True, exist_ok=True)
        else:
            Path(body.path).touch()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class DeleteItem(BaseModel):
    path: str


@router.post("/delete")
async def delete_item(body: DeleteItem):
    p = Path(body.path)
    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/upload")
async def upload(path: str, file: UploadFile = File(...)):
    dest = Path(path) / file.filename
    try:
        with open(dest, "wb") as f:
            content = await file.read()
            f.write(content)
        return {"ok": True, "path": str(dest)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/download")
async def download(path: str):
    p = Path(path)
    if p.is_file():
        return FileResponse(p, filename=p.name)
    return {"error": "Not a file"}
