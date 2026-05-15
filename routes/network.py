import subprocess
from fastapi import APIRouter

router = APIRouter()


@router.get("/interfaces")
async def interfaces():
    r = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True)
    import json
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


@router.get("/connections")
async def connections():
    r = subprocess.run(["ss", "-tunap"], capture_output=True, text=True)
    lines = r.stdout.strip().split("\n")
    conns = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 5:
            conns.append({
                "proto": parts[0],
                "state": parts[1],
                "recv_q": parts[2],
                "send_q": parts[3],
                "local": parts[4],
                "peer": parts[5] if len(parts) > 5 else "",
                "process": parts[6] if len(parts) > 6 else "",
            })
    return conns


@router.get("/wifi")
async def wifi():
    r = subprocess.run(["iw", "dev", "wlan0", "link"], capture_output=True, text=True)
    info = {}
    for line in r.stdout.split("\n"):
        line = line.strip()
        if line.startswith("SSID:"):
            info["ssid"] = line.split("SSID: ")[1]
        elif line.startswith("signal:"):
            info["signal"] = line.split("signal: ")[1]
        elif line.startswith("rx bitrate:"):
            info["bitrate"] = line.split("rx bitrate: ")[1]
        elif line.startswith("freq:"):
            info["frequency"] = line.split("freq: ")[1]
    return info
