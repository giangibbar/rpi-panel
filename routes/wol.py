import json
import socket
import struct
import subprocess
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

DEVICES_FILE = Path(__file__).parent.parent / "wol_devices.json"


def load_devices() -> list:
    if DEVICES_FILE.exists():
        return json.loads(DEVICES_FILE.read_text())
    return []


def save_devices(devices: list):
    DEVICES_FILE.write_text(json.dumps(devices, indent=2))


@router.get("/devices")
async def list_devices():
    return load_devices()


class Device(BaseModel):
    name: str
    mac: str
    ip: str = ""


@router.post("/add")
async def add_device(body: Device):
    devices = load_devices()
    devices.append({"name": body.name, "mac": body.mac, "ip": body.ip})
    save_devices(devices)
    return {"ok": True}


class RemoveDevice(BaseModel):
    mac: str


@router.post("/remove")
async def remove_device(body: RemoveDevice):
    devices = [d for d in load_devices() if d["mac"] != body.mac]
    save_devices(devices)
    return {"ok": True}


class WakeDevice(BaseModel):
    mac: str


@router.post("/wake")
async def wake(body: WakeDevice):
    """Send magic packet to wake a device."""
    mac = body.mac.replace(":", "").replace("-", "")
    if len(mac) != 12:
        return {"ok": False, "error": "Invalid MAC"}
    data = b'\xff' * 6 + bytes.fromhex(mac) * 16
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(data, ('255.255.255.255', 9))
    sock.close()
    return {"ok": True, "message": f"Magic packet sent to {body.mac}"}


@router.get("/scan")
async def scan_network():
    """Scan local network for devices (ARP table)."""
    r = subprocess.run(["ip", "neigh", "show"], capture_output=True, text=True)
    devices = []
    for line in r.stdout.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 5 and parts[2] == "lladdr":
            devices.append({"ip": parts[0], "mac": parts[4], "state": parts[-1]})
    return devices
