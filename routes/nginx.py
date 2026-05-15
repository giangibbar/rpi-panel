import subprocess
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

SITES_DIR = Path("/etc/nginx/sites-available")
ENABLED_DIR = Path("/etc/nginx/sites-enabled")


@router.get("/status")
async def status():
    r = subprocess.run(["systemctl", "is-active", "nginx"], capture_output=True, text=True)
    installed = r.returncode == 0 or "inactive" in r.stdout
    return {"installed": installed or SITES_DIR.exists(), "active": r.stdout.strip() == "active"}


@router.get("/sites")
async def list_sites():
    if not SITES_DIR.exists():
        return []
    sites = []
    for f in SITES_DIR.iterdir():
        enabled = (ENABLED_DIR / f.name).exists()
        sites.append({"name": f.name, "enabled": enabled, "content": f.read_text()})
    return sites


class SiteConfig(BaseModel):
    name: str
    server_name: str = "_"
    proxy_port: int = 8080
    listen: int = 80


@router.post("/create-proxy")
async def create_proxy(body: SiteConfig):
    config = f"""server {{
    listen {body.listen};
    server_name {body.server_name};

    location / {{
        proxy_pass http://127.0.0.1:{body.proxy_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
"""
    r = subprocess.run(["sudo", "tee", f"/etc/nginx/sites-available/{body.name}"], input=config, capture_output=True, text=True)
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr.strip()}
    subprocess.run(["sudo", "ln", "-sf", f"/etc/nginx/sites-available/{body.name}", f"/etc/nginx/sites-enabled/{body.name}"], capture_output=True)
    subprocess.run(["sudo", "nginx", "-t"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "reload", "nginx"], capture_output=True)
    return {"ok": True}


class SiteAction(BaseModel):
    name: str


@router.post("/enable")
async def enable_site(body: SiteAction):
    subprocess.run(["sudo", "ln", "-sf", f"/etc/nginx/sites-available/{body.name}", f"/etc/nginx/sites-enabled/{body.name}"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "reload", "nginx"], capture_output=True)
    return {"ok": True}


@router.post("/disable")
async def disable_site(body: SiteAction):
    subprocess.run(["sudo", "rm", "-f", f"/etc/nginx/sites-enabled/{body.name}"], capture_output=True)
    subprocess.run(["sudo", "systemctl", "reload", "nginx"], capture_output=True)
    return {"ok": True}
