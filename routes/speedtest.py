"""Speedtest: scheduled internet speed tests with history."""

import json
import sqlite3
import subprocess
import threading
import time
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

DB_PATH = Path(__file__).parent.parent / "speedtest.db"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS speedtest (
        id INTEGER PRIMARY KEY, ts INTEGER,
        download REAL, upload REAL, ping REAL, server TEXT
    )""")
    return db


def run_speedtest() -> dict | None:
    try:
        r = subprocess.run(
            ["/home/egamgia/web-terminal/.venv/bin/speedtest-cli", "--json"],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            result = {
                "download": round(data["download"] / 1_000_000, 2),
                "upload": round(data["upload"] / 1_000_000, 2),
                "ping": round(data["ping"], 1),
                "server": data.get("server", {}).get("name", ""),
                "ts": int(time.time()),
            }
            db = get_db()
            db.execute("INSERT INTO speedtest (ts, download, upload, ping, server) VALUES (?,?,?,?,?)",
                       (result["ts"], result["download"], result["upload"], result["ping"], result["server"]))
            db.commit()
            db.close()
            return result
    except Exception:
        pass
    return None


# Scheduled: run every hour
def _scheduler():
    while True:
        run_speedtest()
        time.sleep(3600)


threading.Thread(target=_scheduler, daemon=True).start()


@router.get("/")
async def get_history(hours: int = 168):
    """Get speedtest history (default: 7 days)."""
    since = int(time.time()) - hours * 3600
    db = get_db()
    rows = db.execute("SELECT ts, download, upload, ping, server FROM speedtest WHERE ts > ? ORDER BY ts", (since,)).fetchall()
    db.close()
    return [{"ts": r[0], "download": r[1], "upload": r[2], "ping": r[3], "server": r[4]} for r in rows]


@router.post("/run")
async def run_now():
    """Trigger a speedtest manually."""
    result = run_speedtest()
    if result:
        return {"ok": True, **result}
    return {"ok": False, "error": "Speedtest failed"}


@router.get("/latest")
async def get_latest():
    """Get the most recent speedtest result."""
    db = get_db()
    row = db.execute("SELECT ts, download, upload, ping, server FROM speedtest ORDER BY ts DESC LIMIT 1").fetchone()
    db.close()
    if row:
        return {"ts": row[0], "download": row[1], "upload": row[2], "ping": row[3], "server": row[4]}
    return {"ts": 0, "download": 0, "upload": 0, "ping": 0, "server": "No data yet"}
