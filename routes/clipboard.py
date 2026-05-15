from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# Simple in-memory clipboard (persists while server runs)
_clipboard: str = ""


@router.get("/")
async def get_clipboard():
    return {"content": _clipboard}


class ClipboardContent(BaseModel):
    content: str


@router.post("/")
async def set_clipboard(body: ClipboardContent):
    global _clipboard
    _clipboard = body.content
    return {"ok": True, "length": len(_clipboard)}
