import subprocess
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def disk_info():
    # Partitions
    r = subprocess.run(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,FSUSED,FSAVAIL,FSUSE%"], capture_output=True, text=True)
    import json
    try:
        lsblk = json.loads(r.stdout)
    except Exception:
        lsblk = {}

    # df
    r2 = subprocess.run(["df", "-h", "--output=source,size,used,avail,pcent,target"], capture_output=True, text=True)
    mounts = []
    for line in r2.stdout.strip().split("\n")[1:]:
        parts = line.split()
        if len(parts) >= 6 and not parts[0].startswith("tmpfs"):
            mounts.append({"device": parts[0], "size": parts[1], "used": parts[2], "avail": parts[3], "percent": parts[4], "mount": parts[5]})

    return {"lsblk": lsblk, "mounts": mounts}
