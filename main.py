import hashlib
import os
import secrets
from fastapi import FastAPI, Request, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

from routes.terminal import router as terminal_router
from routes.system import router as system_router
from routes.services import router as services_router
from routes.files import router as files_router
from routes.network import router as network_router
from routes.packages import router as packages_router
from routes.gpio import router as gpio_router
from routes.cron import router as cron_router
from routes.power import router as power_router
from routes.history import router as history_router
from routes.alerts import router as alerts_router
from routes.scripts import router as scripts_router
from routes.camera import router as camera_router
from routes.clipboard import router as clipboard_router
from routes.sshkeys import router as sshkeys_router
from routes.backup import router as backup_router
from routes.tailscale import router as tailscale_router
from routes.bandwidth import router as bandwidth_router
from routes.timezone import router as timezone_router
from routes.users import router as users_router
from routes.venv import router as venv_router
from routes.nginx import router as nginx_router
from routes.firewall import router as firewall_router
from routes.logs import router as logs_router
from routes.disk import router as disk_router
from routes.ollama import router as ollama_router
from routes.notes import router as notes_router
from routes.wol import router as wol_router
from routes.telegram import router as telegram_router
from routes.sensors import router as sensors_router

app = FastAPI()

# Auth
USERNAME = os.environ.get("TERM_USER", "admin")
PASSWORD = os.environ.get("TERM_PASS", "changeme")
SECRET = secrets.token_hex(32)
SESSIONS: set[str] = set()


def make_token(user: str) -> str:
    return hashlib.sha256(f"{SECRET}:{user}".encode()).hexdigest()


def check_auth(token: str | None) -> bool:
    return token in SESSIONS


app.state.check_auth = check_auth

# Routers
app.include_router(terminal_router)
app.include_router(system_router, prefix="/api/system")
app.include_router(services_router, prefix="/api/services")
app.include_router(files_router, prefix="/api/files")
app.include_router(network_router, prefix="/api/network")
app.include_router(packages_router, prefix="/api/packages")
app.include_router(gpio_router, prefix="/api/gpio")
app.include_router(cron_router, prefix="/api/cron")
app.include_router(power_router, prefix="/api/power")
app.include_router(history_router, prefix="/api/history")
app.include_router(alerts_router, prefix="/api/alerts")
app.include_router(scripts_router, prefix="/api/scripts")
app.include_router(camera_router, prefix="/api/camera")
app.include_router(clipboard_router, prefix="/api/clipboard")
app.include_router(sshkeys_router, prefix="/api/sshkeys")
app.include_router(backup_router, prefix="/api/backup")
app.include_router(tailscale_router, prefix="/api/tailscale")
app.include_router(bandwidth_router, prefix="/api/bandwidth")
app.include_router(timezone_router, prefix="/api/timezone")
app.include_router(users_router, prefix="/api/users")
app.include_router(venv_router, prefix="/api/venv")
app.include_router(nginx_router, prefix="/api/nginx")
app.include_router(firewall_router, prefix="/api/firewall")
app.include_router(logs_router, prefix="/api/logs")
app.include_router(disk_router, prefix="/api/disk")
app.include_router(ollama_router, prefix="/api/ollama")
app.include_router(notes_router, prefix="/api/notes")
app.include_router(wol_router, prefix="/api/wol")
app.include_router(telegram_router, prefix="/api/telegram")
app.include_router(sensors_router, prefix="/api/sensors")


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    if form.get("username") == USERNAME and form.get("password") == PASSWORD:
        token = make_token(USERNAME)
        SESSIONS.add(token)
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie("session", token, httponly=True, max_age=86400)
        return resp
    return HTMLResponse(login_page(error=True), status_code=401)


@app.get("/logout")
async def logout(session: str = Cookie(default="")):
    SESSIONS.discard(session)
    resp = RedirectResponse("/login")
    resp.delete_cookie("session")
    return resp


@app.get("/login")
async def login_page_get():
    return HTMLResponse(login_page())


@app.get("/")
async def index(session: str = Cookie(default="")):
    if not check_auth(session):
        return RedirectResponse("/login")
    html = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html.read_text())


def login_page(error=False):
    err = '<p style="color:#f38ba8">Username o password errati</p>' if error else ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login - RPi Panel</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#1e1e2e;display:flex;align-items:center;justify-content:center;height:100vh;font-family:monospace}}
form{{background:#313244;padding:32px;border-radius:8px;width:300px}}
h2{{color:#cdd6f4;margin-bottom:16px;text-align:center}}
input{{width:100%;padding:10px;margin:8px 0;border:1px solid #585b70;border-radius:4px;background:#1e1e2e;color:#cdd6f4;font-size:14px}}
button{{width:100%;padding:10px;margin-top:12px;background:#a6e3a1;border:none;border-radius:4px;font-weight:bold;cursor:pointer;font-size:14px}}
button:hover{{background:#94e2d5}}
p{{margin-top:8px;text-align:center;font-size:12px}}
</style></head><body>
<form method="POST" action="/login">
<h2>🖥️ RPi Panel</h2>
{err}
<input name="username" placeholder="Username" autofocus>
<input name="password" type="password" placeholder="Password">
<button type="submit">Login</button>
</form></body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
