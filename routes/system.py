import subprocess
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()


@router.get("/stats")
async def stats():
    # CPU usage
    with open("/proc/stat") as f:
        cpu_line = f.readline().split()
    idle = int(cpu_line[4])
    total = sum(int(x) for x in cpu_line[1:])

    # Memory
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            parts = line.split()
            mem[parts[0].rstrip(":")] = int(parts[1])
    mem_total = mem["MemTotal"]
    mem_avail = mem["MemAvailable"]
    mem_used = mem_total - mem_avail

    # Temperature
    temp = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000

    # Disk
    st = subprocess.run(["df", "-B1", "/"], capture_output=True, text=True)
    parts = st.stdout.strip().split("\n")[1].split()
    disk_total = int(parts[1])
    disk_used = int(parts[2])

    # Uptime
    uptime_sec = float(Path("/proc/uptime").read_text().split()[0])

    # Load average
    load = Path("/proc/loadavg").read_text().split()[:3]

    # Top processes
    ps = subprocess.run(
        ["ps", "aux", "--sort=-%cpu"], capture_output=True, text=True
    )
    procs = []
    for line in ps.stdout.strip().split("\n")[1:11]:
        p = line.split(None, 10)
        procs.append({"user": p[0], "pid": p[1], "cpu": p[2], "mem": p[3], "cmd": p[10] if len(p) > 10 else ""})

    return {
        "cpu_idle": idle,
        "cpu_total": total,
        "mem_total_mb": mem_total // 1024,
        "mem_used_mb": mem_used // 1024,
        "mem_percent": round(mem_used / mem_total * 100, 1),
        "temp_c": round(temp, 1),
        "disk_total_gb": round(disk_total / 1e9, 1),
        "disk_used_gb": round(disk_used / 1e9, 1),
        "disk_percent": round(disk_used / disk_total * 100, 1),
        "uptime_sec": int(uptime_sec),
        "load": load,
        "processes": procs,
    }
