import json
import time
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

NOTES_FILE = Path(__file__).parent.parent / "notes.json"


def load_notes() -> list:
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text())
    return []


def save_notes(notes: list):
    NOTES_FILE.write_text(json.dumps(notes, indent=2))


@router.get("/")
async def list_notes():
    return load_notes()


class Note(BaseModel):
    title: str
    content: str


@router.post("/create")
async def create_note(body: Note):
    notes = load_notes()
    notes.insert(0, {"id": int(time.time()*1000), "title": body.title, "content": body.content, "created": time.time()})
    save_notes(notes)
    return {"ok": True}


class UpdateNote(BaseModel):
    id: int
    title: str
    content: str


@router.post("/update")
async def update_note(body: UpdateNote):
    notes = load_notes()
    for n in notes:
        if n["id"] == body.id:
            n["title"] = body.title
            n["content"] = body.content
            break
    save_notes(notes)
    return {"ok": True}


class DeleteNote(BaseModel):
    id: int


@router.post("/delete")
async def delete_note(body: DeleteNote):
    notes = [n for n in load_notes() if n["id"] != body.id]
    save_notes(notes)
    return {"ok": True}
