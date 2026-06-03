"""MQTT broker management: status, topics, live messages, publish, clients."""

import json
import subprocess
import threading
import time
from collections import deque
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter()

# Store recent messages per topic (max 50 per topic, max 100 topics)
_messages: dict[str, deque] = {}
_messages_lock = threading.Lock()
_mqtt_client = None

BROKER_USER = "homebot"
BROKER_PASS = "casa2026"


def _start_mqtt_monitor():
    """Background thread: subscribe to # and collect all messages."""
    global _mqtt_client
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        return

    def on_message(client, userdata, msg):
        topic = msg.topic
        try:
            payload = msg.payload.decode()
        except Exception:
            payload = str(msg.payload)
        entry = {"topic": topic, "payload": payload, "ts": int(time.time()), "from": _last_publisher.get(topic, "")}
        with _messages_lock:
            if topic not in _messages:
                if len(_messages) > 100:
                    oldest = min(_messages, key=lambda t: _messages[t][-1]["ts"] if _messages[t] else 0)
                    del _messages[oldest]
                _messages[topic] = deque(maxlen=50)
            _messages[topic].append(entry)
        # Notify websocket subscribers
        for q in _ws_queues:
            q.append(entry)

    client = mqtt.Client()
    client.username_pw_set(BROKER_USER, BROKER_PASS)
    client.on_message = on_message
    try:
        client.connect("localhost", 1883, 60)
        client.subscribe("#")
        _mqtt_client = client
        client.loop_forever()
    except Exception:
        pass


_ws_queues: list[deque] = []
_last_publisher: dict[str, str] = {}  # topic -> last client_id


def _tail_log():
    """Tail mosquitto log to track who publishes what."""
    import re
    try:
        proc = subprocess.Popen(["sudo", "tail", "-f", "/var/log/mosquitto/mosquitto.log"],
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        for line in proc.stdout:
            # Match: "Received PUBLISH from <client_id> (dX, qX, ..., 'topic', ...)"
            m = re.search(r"Received PUBLISH from (\S+) .+?'(.+?)'", line)
            if m:
                _last_publisher[m.group(2)] = m.group(1)
    except Exception:
        pass


threading.Thread(target=_tail_log, daemon=True).start()
threading.Thread(target=_start_mqtt_monitor, daemon=True).start()


@router.get("/status")
async def broker_status():
    """Get Mosquitto broker status."""
    try:
        r = subprocess.run(["systemctl", "is-active", "mosquitto"], capture_output=True, text=True)
        active = r.stdout.strip() == "active"
    except Exception:
        active = False
    # Get connected clients from mosquitto
    clients = []
    try:
        r = subprocess.run(
            ["mosquitto_sub", "-h", "localhost", "-u", BROKER_USER, "-P", BROKER_PASS,
             "-t", "$SYS/broker/clients/connected", "-C", "1", "-W", "2"],
            capture_output=True, text=True, timeout=5
        )
        connected_count = int(r.stdout.strip()) if r.stdout.strip() else 0
    except Exception:
        connected_count = -1
    return {"active": active, "connected_clients": connected_count, "topics_tracked": len(_messages)}


@router.get("/topics")
async def list_topics():
    """List all observed topics with last message and count."""
    # Get subscriber info from mosquitto
    subs = _get_subscriptions()
    with _messages_lock:
        result = []
        for topic, msgs in sorted(_messages.items()):
            last = msgs[-1] if msgs else None
            # Find subscribers matching this topic
            subscribers = []
            for client_id, client_topics in subs.items():
                for ct in client_topics:
                    if ct == "#" or ct == topic or (ct.endswith("/#") and topic.startswith(ct[:-2])):
                        subscribers.append(client_id)
                        break
            result.append({
                "topic": topic,
                "count": len(msgs),
                "last_payload": last["payload"] if last else None,
                "last_ts": last["ts"] if last else None,
                "subscribers": subscribers,
            })
    return result


@router.get("/clients")
async def list_clients():
    """List connected clients and their subscriptions."""
    return _get_subscriptions()


def _get_subscriptions() -> dict[str, list[str]]:
    """Parse mosquitto log for current subscriptions."""
    subs: dict[str, list[str]] = {}
    try:
        r = subprocess.run(
            ["sudo", "grep", "-a", "New client\\|New connection from\\|SUBSCRIBE", "/var/log/mosquitto/mosquitto.log"],
            capture_output=True, text=True, timeout=3
        )
        # Track latest clients and their subs
        import re
        for line in r.stdout.split("\n")[-200:]:
            m = re.search(r"New client connected from .+ as (.+?) ", line)
            if m:
                cid = m.group(1).rstrip(".")
                if cid not in subs:
                    subs[cid] = []
            m = re.search(r"New connection from .+? on port", line)
            # Look for SUBSCRIBE lines
            if "SUBSCRIBE" in line:
                m2 = re.search(r"client (.+?) subscribed to (.+?)$", line)
                if not m2:
                    m2 = re.search(r"(\S+) \d+ (.+)", line)
                if m2:
                    cid = m2.group(1)
                    topic = m2.group(2).strip()
                    subs.setdefault(cid, [])
                    if topic not in subs[cid]:
                        subs[cid].append(topic)
    except Exception:
        pass
    return subs


@router.get("/messages/{topic:path}")
async def get_messages(topic: str, limit: int = 20):
    """Get recent messages for a topic."""
    with _messages_lock:
        msgs = _messages.get(topic, deque())
        return list(msgs)[-limit:]


class PublishRequest(BaseModel):
    topic: str
    payload: str
    retain: bool = False


@router.post("/publish")
async def publish(body: PublishRequest):
    """Publish a message to a topic."""
    if _mqtt_client and _mqtt_client.is_connected():
        _mqtt_client.publish(body.topic, body.payload, retain=body.retain)
        return {"ok": True}
    # Fallback to CLI
    cmd = ["mosquitto_pub", "-h", "localhost", "-u", BROKER_USER, "-P", BROKER_PASS,
           "-t", body.topic, "-m", body.payload]
    if body.retain:
        cmd.append("-r")
    subprocess.run(cmd, timeout=5)
    return {"ok": True}


@router.websocket("/live")
async def live_messages(websocket: WebSocket):
    """WebSocket stream of all incoming MQTT messages."""
    import asyncio
    await websocket.accept()
    q: deque = deque(maxlen=100)
    _ws_queues.append(q)
    try:
        while True:
            if q:
                msg = q.popleft()
                await websocket.send_json(msg)
            else:
                await asyncio.sleep(0.2)
    except Exception:
        pass
    finally:
        _ws_queues.remove(q)
