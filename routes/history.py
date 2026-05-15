import sqlite3
import time
import threading
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

DB_PATH = Path(__file__).parent.parent / "history.db"


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""CREATE TABLE IF NOT EXISTS metrics (
        ts INTEGER PRIMARY KEY,
        cpu_load REAL,
        temp REAL,
        mem_percent REAL,
        disk_percent REAL
    )""")
    return db


def collect_metrics():
    """Background thread: collect metrics every 30s."""
    while True:
        try:
            # CPU load
            load = float(Path("/proc/loadavg").read_text().split()[0])
            # Temp
            temp = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000
            # Memory
            mem = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    mem[parts[0].rstrip(":")] = int(parts[1])
            mem_pct = round((mem["MemTotal"] - mem["MemAvailable"]) / mem["MemTotal"] * 100, 1)
            # Disk
            import subprocess
            r = subprocess.run(["df", "--output=pcent", "/"], capture_output=True, text=True)
            disk_pct = float(r.stdout.strip().split("\n")[1].strip().rstrip("%"))

            db = get_db()
            db.execute("INSERT OR REPLACE INTO metrics VALUES (?,?,?,?,?)",
                       (int(time.time()), load, round(temp, 1), mem_pct, disk_pct))
            db.execute("DELETE FROM metrics WHERE ts < ?", (int(time.time()) - 86400,))  # keep 24h
            db.commit()
            db.close()
        except Exception:
            pass
        time.sleep(30)


# Start collector thread
_thread = threading.Thread(target=collect_metrics, daemon=True)
_thread.start()


@router.get("/")
async def get_history(hours: int = 6):
    """Get metrics for the last N hours."""
    since = int(time.time()) - hours * 3600
    db = get_db()
    rows = db.execute("SELECT ts, cpu_load, temp, mem_percent, disk_percent FROM metrics WHERE ts > ? ORDER BY ts", (since,)).fetchall()
    db.close()
    return {
        "timestamps": [r[0] for r in rows],
        "cpu_load": [r[1] for r in rows],
        "temp": [r[2] for r in rows],
        "mem_percent": [r[3] for r in rows],
        "disk_percent": [r[4] for r in rows],
    }
