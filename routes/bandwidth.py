from pathlib import Path
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def bandwidth():
    """Get current network traffic stats."""
    stats = {}
    for iface in ["wlan0", "eth0"]:
        rx_path = Path(f"/sys/class/net/{iface}/statistics/rx_bytes")
        tx_path = Path(f"/sys/class/net/{iface}/statistics/tx_bytes")
        if rx_path.exists():
            stats[iface] = {
                "rx_bytes": int(rx_path.read_text().strip()),
                "tx_bytes": int(tx_path.read_text().strip()),
            }
    return stats
