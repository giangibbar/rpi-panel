import asyncio
import os
import pty
import select
import struct
import fcntl
import termios
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie

router = APIRouter()


@router.websocket("/ws/terminal")
async def terminal(ws: WebSocket, session: str = Cookie(default="")):
    check_auth = ws.app.state.check_auth
    if not check_auth(session):
        await ws.close(code=4001)
        return

    await ws.accept()

    pid, fd = pty.openpty()
    child_pid = os.fork()

    if child_pid == 0:
        os.close(pid)
        os.setsid()
        os.dup2(fd, 0)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        os.close(fd)
        os.execvp("/bin/bash", ["/bin/bash", "--login"])
    else:
        os.close(fd)

        async def read_output():
            try:
                while True:
                    await asyncio.sleep(0.01)
                    if select.select([pid], [], [], 0)[0]:
                        data = os.read(pid, 4096)
                        if data:
                            await ws.send_text(data.decode("utf-8", errors="replace"))
                        else:
                            break
            except (OSError, WebSocketDisconnect):
                pass

        reader_task = asyncio.create_task(read_output())

        try:
            while True:
                msg = await ws.receive_json()
                if msg.get("type") == "input":
                    os.write(pid, msg["data"].encode("utf-8"))
                elif msg.get("type") == "resize":
                    winsize = struct.pack("HHHH", msg.get("rows", 24), msg.get("cols", 80), 0, 0)
                    fcntl.ioctl(pid, termios.TIOCSWINSZ, winsize)
        except WebSocketDisconnect:
            pass
        finally:
            reader_task.cancel()
            os.kill(child_pid, 9)
            os.waitpid(child_pid, 0)
            os.close(pid)
