import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

CONFIG_PATH = Path(__file__).parent.parent / "alerts.json"

DEFAULT_CONFIG = {
    "temp_max": 70,
    "mem_max": 90,
    "disk_max": 85,
    "load_max": 3.5,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


@router.get("/config")
async def get_config():
    return load_config()


class AlertConfig(BaseModel):
    temp_max: float = 70
    mem_max: float = 90
    disk_max: float = 85
    load_max: float = 3.5


@router.post("/config")
async def set_config(body: AlertConfig):
    cfg = body.model_dump()
    save_config(cfg)
    return {"ok": True}


@router.get("/check")
async def check_alerts():
    """Check current values against thresholds."""
    cfg = load_config()
    alerts = []

    # Temp
    temp = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000
    if temp > cfg["temp_max"]:
        alerts.append({"type": "temp", "message": f"Temperature {temp:.1f}°C exceeds {cfg['temp_max']}°C", "severity": "critical"})

    # Memory
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            parts = line.split()
            mem[parts[0].rstrip(":")] = int(parts[1])
    mem_pct = (mem["MemTotal"] - mem["MemAvailable"]) / mem["MemTotal"] * 100
    if mem_pct > cfg["mem_max"]:
        alerts.append({"type": "mem", "message": f"Memory {mem_pct:.1f}% exceeds {cfg['mem_max']}%", "severity": "warning"})

    # Disk
    import subprocess
    r = subprocess.run(["df", "--output=pcent", "/"], capture_output=True, text=True)
    disk_pct = float(r.stdout.strip().split("\n")[1].strip().rstrip("%"))
    if disk_pct > cfg["disk_max"]:
        alerts.append({"type": "disk", "message": f"Disk {disk_pct:.0f}% exceeds {cfg['disk_max']}%", "severity": "warning"})

    # Load
    load = float(Path("/proc/loadavg").read_text().split()[0])
    if load > cfg["load_max"]:
        alerts.append({"type": "load", "message": f"Load {load:.2f} exceeds {cfg['load_max']}", "severity": "warning"})

    return {"alerts": alerts, "values": {"temp": round(temp, 1), "mem": round(mem_pct, 1), "disk": round(disk_pct, 1), "load": load}}
