import subprocess
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

OLLAMA_URL = "http://localhost:11434"


@router.get("/status")
async def status():
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = r.json().get("models", [])
        return {"running": True, "models": [m["name"] for m in models]}
    except Exception:
        return {"running": False, "models": []}


@router.post("/install")
async def install():
    r = subprocess.Popen(["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"ok": True, "message": "Installing in background..."}


class PullModel(BaseModel):
    model: str = "qwen2.5:1.5b"


@router.post("/pull")
async def pull(body: PullModel):
    r = subprocess.run(["ollama", "pull", body.model], capture_output=True, text=True, timeout=600)
    return {"ok": r.returncode == 0, "output": r.stdout + r.stderr}


class ChatMessage(BaseModel):
    model: str = "qwen2.5:1.5b"
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(body: ChatMessage):
    messages = body.history + [{"role": "user", "content": body.message}]
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", json={"model": body.model, "messages": messages, "stream": False}, timeout=120)
        data = r.json()
        return {"reply": data.get("message", {}).get("content", ""), "ok": True}
    except httpx.TimeoutException:
        return {"reply": "Timeout — model too slow", "ok": False}
    except Exception as e:
        return {"reply": str(e), "ok": False}
