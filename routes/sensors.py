import json
import sqlite3
import time
import threading
import subprocess
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

DB_PATH = Path(__file__).parent.parent / "sensors.db"
SENSORS_FILE = Path(__file__).parent.parent / "sensors_config.json"

# Wiring diagrams for common sensors
WIRING_DIAGRAMS = {
    "DHT22": {
        "description": "Temperature & Humidity",
        "pins": {"VCC": "3.3V (pin 1)", "DATA": "GPIO4 (pin 7)", "GND": "GND (pin 9)"},
        "notes": "Add 10kΩ pull-up resistor between VCC and DATA",
        "protocol": "1-Wire",
        "library": "adafruit-circuitpython-dht",
    },
    "BME280": {
        "description": "Temp, Humidity, Pressure (I2C)",
        "pins": {"VIN": "3.3V (pin 1)", "GND": "GND (pin 6)", "SCL": "GPIO3/SCL (pin 5)", "SDA": "GPIO2/SDA (pin 3)"},
        "notes": "I2C address: 0x76 or 0x77. Enable I2C in raspi-config",
        "protocol": "I2C",
        "library": "adafruit-circuitpython-bme280",
    },
    "BMP280": {
        "description": "Temp & Pressure (I2C)",
        "pins": {"VIN": "3.3V (pin 1)", "GND": "GND (pin 6)", "SCL": "GPIO3/SCL (pin 5)", "SDA": "GPIO2/SDA (pin 3)"},
        "notes": "I2C address: 0x76 or 0x77",
        "protocol": "I2C",
        "library": "adafruit-circuitpython-bmp280",
    },
    "DS18B20": {
        "description": "Waterproof Temperature",
        "pins": {"VCC": "3.3V (pin 1)", "DATA": "GPIO4 (pin 7)", "GND": "GND (pin 9)"},
        "notes": "Add 4.7kΩ pull-up between VCC and DATA. Enable 1-Wire in config.txt: dtoverlay=w1-gpio",
        "protocol": "1-Wire",
        "library": "w1thermsensor",
    },
    "MQ-2": {
        "description": "Gas/Smoke sensor (analog → needs ADC)",
        "pins": {"VCC": "5V (pin 2)", "GND": "GND (pin 6)", "DOUT": "GPIO17 (pin 11)", "AOUT": "ADS1115 A0"},
        "notes": "Digital output for threshold, analog needs ADS1115 ADC via I2C",
        "protocol": "GPIO/I2C (via ADC)",
        "library": "adafruit-circuitpython-ads1x15",
    },
    "HC-SR04": {
        "description": "Ultrasonic Distance",
        "pins": {"VCC": "5V (pin 2)", "TRIG": "GPIO23 (pin 16)", "ECHO": "GPIO24 (pin 18) via voltage divider", "GND": "GND (pin 20)"},
        "notes": "ECHO is 5V! Use voltage divider (1kΩ + 2kΩ) to bring to 3.3V",
        "protocol": "GPIO",
        "library": "gpiozero (DistanceSensor)",
    },
    "PIR_HC-SR501": {
        "description": "Motion Detector",
        "pins": {"VCC": "5V (pin 2)", "OUT": "GPIO17 (pin 11)", "GND": "GND (pin 6)"},
        "notes": "Adjust sensitivity and delay with onboard potentiometers",
        "protocol": "GPIO",
        "library": "gpiozero (MotionSensor)",
    },
    "RELAY_MODULE": {
        "description": "Relay (switch high-power devices)",
        "pins": {"VCC": "5V (pin 2)", "IN": "GPIO18 (pin 12)", "GND": "GND (pin 14)"},
        "notes": "Active LOW. Use for lights, fans, pumps. Max 10A/250VAC",
        "protocol": "GPIO",
        "library": "gpiozero (OutputDevice)",
    },
    "ESP32_MQTT": {
        "description": "ESP32/ESP8266 via WiFi+MQTT",
        "pins": {"connection": "WiFi → MQTT broker on RPi (port 1883)"},
        "notes": "Flash ESP with Arduino/MicroPython. Publish to topic: sensors/<device_id>/<metric>",
        "protocol": "MQTT",
        "library": "paho-mqtt (RPi side), PubSubClient (ESP side)",
    },
    "ARDUINO_SERIAL": {
        "description": "Arduino via USB Serial",
        "pins": {"connection": "USB cable RPi ↔ Arduino (/dev/ttyUSB0 or /dev/ttyACM0)"},
        "notes": "Arduino sends JSON lines: {\"temp\":22.5,\"humidity\":45}. Baud: 9600",
        "protocol": "Serial",
        "library": "pyserial",
    },
}


def get_db():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("""CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sensor_id TEXT NOT NULL,
        metric TEXT NOT NULL,
        value REAL NOT NULL,
        ts INTEGER NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_data(sensor_id, ts)")
    return db


def load_sensors() -> list:
    if SENSORS_FILE.exists():
        return json.loads(SENSORS_FILE.read_text())
    return []


def save_sensors(sensors: list):
    SENSORS_FILE.write_text(json.dumps(sensors, indent=2))


@router.get("/catalog")
async def catalog():
    """Get supported sensor types with wiring diagrams."""
    custom = load_custom_types()
    return {**WIRING_DIAGRAMS, **custom}


CUSTOM_TYPES_FILE = Path(__file__).parent.parent / "custom_sensor_types.json"


def load_custom_types() -> dict:
    if CUSTOM_TYPES_FILE.exists():
        return json.loads(CUSTOM_TYPES_FILE.read_text())
    return {}


def save_custom_types(types: dict):
    CUSTOM_TYPES_FILE.write_text(json.dumps(types, indent=2))


class CustomSensorType(BaseModel):
    key: str
    description: str
    pins: dict  # {"VCC": "3.3V (pin 1)", "DATA": "GPIO4 (pin 7)", ...}
    notes: str = ""
    protocol: str = "GPIO"
    library: str = ""


@router.post("/catalog/add")
async def add_custom_type(body: CustomSensorType):
    types = load_custom_types()
    types[body.key] = body.model_dump(exclude={"key"})
    save_custom_types(types)
    return {"ok": True}


@router.post("/catalog/remove")
async def remove_custom_type(body: RemoveSensor):
    types = load_custom_types()
    types.pop(body.id, None)
    save_custom_types(types)
    return {"ok": True}


@router.get("/")
async def list_sensors():
    return load_sensors()


class RegisterSensor(BaseModel):
    id: str
    name: str
    type: str  # key from WIRING_DIAGRAMS
    gpio_pin: int | None = None
    mqtt_topic: str = ""
    serial_port: str = ""


@router.post("/register")
async def register_sensor(body: RegisterSensor):
    sensors = load_sensors()
    sensors.append(body.model_dump())
    save_sensors(sensors)
    return {"ok": True}


class RemoveSensor(BaseModel):
    id: str


@router.post("/remove")
async def remove_sensor(body: RemoveSensor):
    sensors = [s for s in load_sensors() if s["id"] != body.id]
    save_sensors(sensors)
    return {"ok": True}


class EditSensor(BaseModel):
    id: str
    name: str = ""
    type: str = ""
    gpio_pin: int | None = None
    mqtt_topic: str = ""
    serial_port: str = ""


@router.post("/edit")
async def edit_sensor(body: EditSensor):
    sensors = load_sensors()
    for s in sensors:
        if s["id"] == body.id:
            if body.name: s["name"] = body.name
            if body.type: s["type"] = body.type
            s["gpio_pin"] = body.gpio_pin
            s["mqtt_topic"] = body.mqtt_topic
            s["serial_port"] = body.serial_port
            break
    save_sensors(sensors)
    return {"ok": True}


class SensorReading(BaseModel):
    sensor_id: str
    metric: str
    value: float


@router.post("/data")
async def push_data(body: SensorReading):
    """Push a sensor reading (from MQTT callback, serial reader, or manual)."""
    db = get_db()
    db.execute("INSERT INTO sensor_data (sensor_id, metric, value, ts) VALUES (?,?,?,?)",
               (body.sensor_id, body.metric, body.value, int(time.time())))
    db.execute("DELETE FROM sensor_data WHERE ts < ?", (int(time.time()) - 7 * 86400,))  # keep 7 days
    db.commit()
    db.close()
    return {"ok": True}


@router.get("/data/{sensor_id}")
async def get_data(sensor_id: str, hours: int = 6):
    since = int(time.time()) - hours * 3600
    db = get_db()
    rows = db.execute("SELECT metric, value, ts FROM sensor_data WHERE sensor_id=? AND ts>? ORDER BY ts",
                      (sensor_id, since)).fetchall()
    db.close()
    # Group by metric
    metrics: dict[str, list] = {}
    for metric, value, ts in rows:
        if metric not in metrics:
            metrics[metric] = {"timestamps": [], "values": []}
        metrics[metric]["timestamps"].append(ts)
        metrics[metric]["values"].append(value)
    return metrics


@router.get("/data/{sensor_id}/latest")
async def get_latest(sensor_id: str):
    db = get_db()
    rows = db.execute(
        "SELECT metric, value, ts FROM sensor_data WHERE sensor_id=? ORDER BY ts DESC LIMIT 10",
        (sensor_id,)
    ).fetchall()
    db.close()
    latest = {}
    for metric, value, ts in rows:
        if metric not in latest:
            latest[metric] = {"value": value, "ts": ts}
    return latest


# MQTT listener thread (if mosquitto is running)
def _mqtt_listener():
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        return

    def on_message(client, userdata, msg):
        # Expected topic: sensors/<sensor_id>/<metric>
        parts = msg.topic.split("/")
        if len(parts) >= 3 and parts[0] == "sensors":
            sensor_id = parts[1]
            metric = parts[2]
            try:
                value = float(msg.payload.decode())
                db = get_db()
                db.execute("INSERT INTO sensor_data (sensor_id, metric, value, ts) VALUES (?,?,?,?)",
                           (sensor_id, metric, value, int(time.time())))
                db.commit()
                db.close()
            except (ValueError, Exception):
                pass

    try:
        client = mqtt.Client()
        client.on_message = on_message
        client.connect("localhost", 1883, 60)
        client.subscribe("sensors/#")
        client.loop_forever()
    except Exception:
        pass


_mqtt_thread = threading.Thread(target=_mqtt_listener, daemon=True)
_mqtt_thread.start()
