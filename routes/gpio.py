import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

CHIP = "gpiochip0"
# RPi4 usable GPIO pins (BCM numbering) on the 40-pin header
USER_PINS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]

# Physical pin mapping for display (BCM -> physical pin, power pins noted)
POWER_PINS = {
    1: "3.3V", 2: "5V", 4: "5V", 6: "GND", 9: "GND", 14: "GND",
    17: "3.3V", 20: "GND", 25: "GND", 30: "GND", 34: "GND", 39: "GND",
}

# Track which pins we've set as output
active_outputs: dict[int, int] = {}


@router.get("/pins")
async def list_pins():
    """List all GPIO pins with their current state."""
    pins = []
    for pin in USER_PINS:
        state = {"pin": pin, "value": None, "direction": "input", "active": pin in active_outputs}
        # Try to read current value
        r = subprocess.run(
            ["gpioget", "--bias=as-is", CHIP, str(pin)],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            state["value"] = int(r.stdout.strip())
        if pin in active_outputs:
            state["direction"] = "output"
            state["value"] = active_outputs[pin]
        pins.append(state)
    return {"pins": pins, "power_pins": POWER_PINS}


class PinWrite(BaseModel):
    pin: int
    value: int  # 0 or 1


@router.post("/write")
async def write_pin(body: PinWrite):
    """Set a pin HIGH or LOW."""
    r = subprocess.run(
        ["gpioset", CHIP, f"{body.pin}={body.value}"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        active_outputs[body.pin] = body.value
        return {"ok": True, "pin": body.pin, "value": body.value}
    return {"ok": False, "error": r.stderr.strip()}


@router.post("/toggle")
async def toggle_pin(body: PinWrite):
    """Toggle a pin. body.value is the current value, we flip it."""
    new_val = 0 if body.value else 1
    r = subprocess.run(
        ["gpioset", CHIP, f"{body.pin}={new_val}"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        active_outputs[body.pin] = new_val
        return {"ok": True, "pin": body.pin, "value": new_val}
    return {"ok": False, "error": r.stderr.strip()}


@router.get("/read/{pin}")
async def read_pin(pin: int):
    """Read a single pin value."""
    r = subprocess.run(
        ["gpioget", "--bias=as-is", CHIP, str(pin)],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        val = int(r.stdout.strip())
        return {"pin": pin, "value": val}
    return {"pin": pin, "error": r.stderr.strip()}


class PinRelease(BaseModel):
    pin: int


@router.post("/release")
async def release_pin(body: PinRelease):
    """Release a pin from output control."""
    active_outputs.pop(body.pin, None)
    return {"ok": True}
