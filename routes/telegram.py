import json
import threading
import time
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
import httpx

router = APIRouter()

CONFIG_FILE = Path(__file__).parent.parent / "telegram.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {"token": "", "chat_id": "", "enabled": False, "alerts": {"temp_high": True, "service_down": True, "ssh_failed": True, "disk_full": True, "process_done": True}}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def send_message(text: str):
    cfg = load_config()
    if not cfg["token"] or not cfg["chat_id"] or not cfg["enabled"]:
        return False
    try:
        url = f"https://api.telegram.org/bot{cfg['token']}/sendMessage"
        httpx.post(url, json={"chat_id": cfg["chat_id"], "text": f"🖥️ RPi Panel\n\n{text}", "parse_mode": "HTML"}, timeout=10)
        return True
    except Exception:
        return False


@router.get("/config")
async def get_config():
    cfg = load_config()
    return {**cfg, "token": "***" if cfg["token"] else ""}


class TelegramConfig(BaseModel):
    token: str = ""
    chat_id: str = ""
    enabled: bool = False
    alerts: dict = {}


@router.post("/config")
async def set_config(body: TelegramConfig):
    cfg = load_config()
    if body.token and body.token != "***":
        cfg["token"] = body.token
    if body.chat_id:
        cfg["chat_id"] = body.chat_id
    cfg["enabled"] = body.enabled
    if body.alerts:
        cfg["alerts"] = body.alerts
    save_config(cfg)
    return {"ok": True}


@router.post("/test")
async def test_message():
    ok = send_message("✅ Test notification — Telegram integration works!")
    return {"ok": ok}


class SendNotification(BaseModel):
    message: str


@router.post("/send")
async def send(body: SendNotification):
    ok = send_message(body.message)
    return {"ok": ok}


# Background monitor thread
def _monitor_loop():
    """Check system health every 60s and send alerts."""
    prev_services = set()
    while True:
        time.sleep(60)
        cfg = load_config()
        if not cfg["enabled"]:
            continue
        alerts = cfg.get("alerts", {})
        try:
            # Temperature
            if alerts.get("temp_high"):
                temp = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000
                if temp > 75:
                    send_message(f"🔥 <b>High temperature!</b> {temp:.1f}°C")

            # Disk
            if alerts.get("disk_full"):
                import subprocess
                r = subprocess.run(["df", "--output=pcent", "/"], capture_output=True, text=True)
                pct = float(r.stdout.strip().split("\n")[1].strip().rstrip("%"))
                if pct > 90:
                    send_message(f"💽 <b>Disk almost full!</b> {pct:.0f}% used")

            # SSH failed
            if alerts.get("ssh_failed"):
                import subprocess
                r = subprocess.run(["journalctl", "-u", "ssh", "--since", "1 min ago", "--no-pager"], capture_output=True, text=True)
                failed = [l for l in r.stdout.split("\n") if "Failed" in l]
                if len(failed) > 3:
                    send_message(f"🚨 <b>{len(failed)} failed SSH attempts</b> in the last minute!")

        except Exception:
            pass


_monitor = threading.Thread(target=_monitor_loop, daemon=True)
_monitor.start()
