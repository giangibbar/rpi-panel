import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


@router.get("/")
async def get_timezone():
    r = subprocess.run(["timedatectl", "show", "--no-pager"], capture_output=True, text=True)
    info = {}
    for line in r.stdout.strip().split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            info[k] = v
    return {"timezone": info.get("Timezone", ""), "ntp": info.get("NTP", ""), "local_time": info.get("TimeUSec", "")}


@router.get("/list")
async def list_timezones():
    r = subprocess.run(["timedatectl", "list-timezones"], capture_output=True, text=True)
    return {"timezones": r.stdout.strip().split("\n")}


class SetTZ(BaseModel):
    timezone: str


@router.post("/set")
async def set_timezone(body: SetTZ):
    r = subprocess.run(["sudo", "timedatectl", "set-timezone", body.timezone], capture_output=True, text=True)
    return {"ok": r.returncode == 0, "error": r.stderr.strip()}
