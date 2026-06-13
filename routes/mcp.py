import json
import time
from collections import deque
import httpx
from fastapi import APIRouter

router = APIRouter()
MCP_URL = "http://127.0.0.1:8002/mcp/"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
call_log = deque(maxlen=50)

async def mcp_request(payload, timeout=30):
    async with httpx.AsyncClient() as c:
        async with c.stream("POST", MCP_URL, headers=HEADERS, json=payload, timeout=timeout) as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    return json.loads(line[6:])
    return None

@router.get("/status")
async def mcp_status():
    try:
        data = await mcp_request({"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}})
        if data:
            tools = data.get("result", {}).get("tools", [])
            return {"online": True, "tool_count": len(tools)}
        return {"online": False, "tool_count": 0}
    except Exception:
        return {"online": False, "tool_count": 0}

@router.get("/tools")
async def mcp_tools():
    try:
        data = await mcp_request({"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}})
        if data:
            return data.get("result", {}).get("tools", [])
        return []
    except Exception:
        return []

@router.post("/call")
async def mcp_call(body: dict):
    tool = body.get("tool", "")
    args = body.get("arguments", {})
    t0 = time.time()
    try:
        data = await mcp_request({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name": tool, "arguments": args}}, timeout=90)
        elapsed = round(time.time() - t0, 2)
        if data:
            result = data.get("result", {})
            content = result.get("content", [])
            text = content[0].get("text", "") if content else ""
            call_log.appendleft({"tool": tool, "args": args, "time": time.strftime("%H:%M:%S"), "elapsed": elapsed, "ok": True})
            return {"ok": True, "result": text, "error": result.get("isError", False)}
        call_log.appendleft({"tool": tool, "args": args, "time": time.strftime("%H:%M:%S"), "elapsed": elapsed, "ok": False})
        return {"ok": False, "result": "No response", "error": True}
    except Exception as e:
        elapsed = round(time.time() - t0, 2)
        call_log.appendleft({"tool": tool, "args": args, "time": time.strftime("%H:%M:%S"), "elapsed": elapsed, "ok": False})
        return {"ok": False, "result": str(e), "error": True}

@router.get("/log")
async def mcp_log():
    # Try server-side log first (captures all calls including direct MCP)
    from pathlib import Path
    log_file = Path("/home/egamgia/mcp-server/calls.json")
    if log_file.exists():
        try:
            return json.loads(log_file.read_text())[:50]
        except Exception:
            pass
    return list(call_log)
