import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


@router.get("/")
async def list_services():
    r = subprocess.run(
        ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"],
        capture_output=True, text=True
    )
    services = []
    for line in r.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split(None, 4)
        if len(parts) >= 4:
            services.append({
                "name": parts[0],
                "load": parts[1],
                "active": parts[2],
                "sub": parts[3],
                "description": parts[4] if len(parts) > 4 else "",
            })
    return services


class ServiceAction(BaseModel):
    name: str


class ServiceCreate(BaseModel):
    name: str
    description: str = ""
    exec_start: str
    working_dir: str = ""
    user: str = "egamgia"
    restart: str = "always"
    after: str = "network.target"
    env: list[str] = []  # ["KEY=value", ...]


@router.post("/create")
async def create_service(body: ServiceCreate):
    unit = f"""[Unit]
Description={body.description or body.name}
After={body.after}

[Service]
Type=simple
User={body.user}
{'WorkingDirectory=' + body.working_dir if body.working_dir else ''}
ExecStart={body.exec_start}
Restart={body.restart}
RestartSec=5
{chr(10).join('Environment=' + e for e in body.env)}

[Install]
WantedBy=multi-user.target
"""
    svc_name = body.name if body.name.endswith('.service') else f"{body.name}.service"
    path = f"/etc/systemd/system/{svc_name}"
    r = subprocess.run(["sudo", "tee", path], input=unit, capture_output=True, text=True)
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr.strip()}
    subprocess.run(["sudo", "systemctl", "daemon-reload"], capture_output=True)
    return {"ok": True, "name": svc_name, "path": path}


@router.post("/start")
async def start(body: ServiceAction):
    r = subprocess.run(["sudo", "systemctl", "start", body.name], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}


@router.post("/stop")
async def stop(body: ServiceAction):
    r = subprocess.run(["sudo", "systemctl", "stop", body.name], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}


@router.post("/restart")
async def restart(body: ServiceAction):
    r = subprocess.run(["sudo", "systemctl", "restart", body.name], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}


@router.get("/logs/{name}")
async def logs(name: str, lines: int = 50):
    r = subprocess.run(
        ["journalctl", "-u", name, "--no-pager", "-n", str(lines), "--output=short"],
        capture_output=True, text=True
    )
    return {"logs": r.stdout}
