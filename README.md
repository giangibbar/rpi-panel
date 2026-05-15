# 🖥️ RPi Panel

A complete web-based management panel for Raspberry Pi 4, built with **FastAPI + vanilla JS**. Access your Pi from any browser — monitor, control, and develop remotely.

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 📊 Monitor
- **Dashboard** — CPU, RAM, temperature, disk, uptime, top processes (auto-refresh)
- **History** — Charts (1h/6h/24h) for CPU load, temperature, memory, disk usage
- **Bandwidth** — Real-time network traffic (upload/download speed per interface)
- **Alerts** — Configurable thresholds with banner notifications

### 💻 Terminal
- Full PTY terminal in the browser (xterm.js)
- Multi-tab support — open/close multiple shell sessions
- Resize-aware, color support, tab completion

### ⚙️ System
- **Services** — List, start/stop/restart systemd services + create new ones via wizard
- **Packages** — Check updates, upgrade, install/remove apt packages
- **Cron** — Manage cron jobs visually
- **Timezone** — View/change timezone, NTP status
- **Users** — Create users, change passwords
- **Telegram** — Bot notifications for temperature, disk, SSH alerts
- **Power** — Reboot/shutdown from the browser

### 📁 Files
- **File Manager** — Browse, create, edit, delete, upload/download files
- **Scripts** — Save and run bash scripts with one click
- **Notes** — Quick notes/todo saved on the Pi

### 🌐 Network
- **Connections** — WiFi info (SSID, signal, speed), active connections
- **Firewall** — UFW enable/disable, add/remove rules
- **Nginx** — Create reverse proxies, enable/disable sites
- **Tailscale** — VPN status, connect/disconnect, setup instructions
- **Wake-on-LAN** — Wake PCs on your network, scan for devices

### 🔌 Hardware
- **GPIO** — Visual 40-pin header, click to set HIGH/LOW, auto-detects kernel pin usage (SPI, I2C, UART)
- **Disk** — Partition info with usage bars
- **Camera** — Take snapshots (if PiCamera connected)

### 🌡️ Sensors & IoT
- **Real-time Board** — Visual drag & drop board with RPi + sensors, live data overlay, wire connections to pins
- **Simulator** — Embedded Wokwi simulator (Arduino, ESP32, RPi Pico)
- **Wiring Guide** — Catalog of supported sensors with pin diagrams + create custom sensor types
- **Manage** — Register sensors (GPIO, I2C, MQTT, Serial) with free-pin dropdown
- **MQTT** — Built-in listener for ESP32/ESP8266 devices (`sensors/<id>/<metric>`)

### 🐍 Dev
- **Venvs** — List Python venvs (version, size, packages), install/upgrade/freeze, run scripts, inline code editor
- **Ollama** — Status, install, pull models

### 🔑 Security
- **SSH Keys** — View/add/remove authorized keys
- **Auth Logs** — Failed SSH attempts, security log
- **Clipboard** — Shared text between PC and Pi
- **Backups** — Create/restore/delete tar.gz backups

### 🤖 AI Chat
- Floating chat panel (accessible from any page via 🤖 button in topbar)
- Powered by Ollama (local LLM, no internet needed)
- Model: qwen2.5:1.5b (fits in 4GB RAM)

### 🎨 UI/UX
- **Circular gauges** on dashboard (CPU, RAM, Temp, Disk) with color transitions
- **Dark/Light theme** toggle (persisted in localStorage)
- **Toast notifications** instead of browser alerts
- **Breadcrumb navigation** in topbar
- **CodeMirror editor** with syntax highlighting for file editing
- **Smooth animations** and card hover effects
- **Inter + JetBrains Mono** fonts
- **Grouped navigation** — 8 categories with sub-tabs
- **GPIO sensor labels** — shows what's connected to each pin

## 🚀 Installation

### Prerequisites
- Raspberry Pi 4 (2GB+ RAM) with Ubuntu/Raspberry Pi OS
- Python 3.11+
- (Optional) Ollama for AI chat
- (Optional) Mosquitto for MQTT sensors

### Quick Start

```bash
# Clone
git clone https://github.com/giangibbar/rpi-panel.git
cd rpi-panel

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Set your username and password

# Run
python main.py
```

Open **http://YOUR_PI_IP:8080** in your browser.

### Production (systemd)

```bash
sudo tee /etc/systemd/system/rpi-panel.service > /dev/null << EOF
[Unit]
Description=RPi Panel
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
EnvironmentFile=$(pwd)/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now rpi-panel
```

### Optional: Ollama (AI Chat)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:1.5b
```

### Optional: MQTT (IoT Sensors)

```bash
sudo apt install -y mosquitto mosquitto-clients
```

ESP32/Arduino publish to: `sensors/<device_id>/<metric>` on port 1883.

### Optional: Tailscale (Remote Access)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

## 📁 Project Structure

```
rpi-panel/
├── main.py              # FastAPI app, auth, router registration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── .gitignore
├── static/
│   └── index.html       # Single-page frontend (vanilla JS)
└── routes/
    ├── terminal.py      # WebSocket PTY terminal
    ├── system.py        # CPU, RAM, temp, disk stats
    ├── services.py      # systemd management
    ├── files.py         # File manager
    ├── network.py       # WiFi, connections
    ├── packages.py      # apt management
    ├── gpio.py          # GPIO control (libgpiod)
    ├── cron.py          # Cron jobs
    ├── power.py         # Reboot/shutdown
    ├── history.py       # Metrics history (SQLite)
    ├── alerts.py        # Threshold alerts
    ├── scripts.py       # Script manager
    ├── camera.py        # PiCamera snapshots
    ├── clipboard.py     # Shared clipboard
    ├── sshkeys.py       # SSH key management
    ├── backup.py        # Backup manager
    ├── tailscale.py     # Tailscale VPN
    ├── bandwidth.py     # Network traffic
    ├── timezone.py      # Timezone/NTP
    ├── users.py         # User management
    ├── venv.py          # Python venv manager
    ├── nginx.py         # Nginx proxy config
    ├── firewall.py      # UFW firewall
    ├── logs.py          # Auth/security logs
    ├── disk.py          # Disk/partition info
    ├── ollama.py        # Ollama LLM chat
    ├── notes.py         # Notes/todo
    ├── wol.py           # Wake-on-LAN
    ├── telegram.py      # Telegram notifications
    └── sensors.py       # IoT sensors + MQTT
```

## 🔒 Security

- Session-based authentication (cookie + SHA256 token)
- Credentials via environment variables (never hardcoded)
- Designed for **local network / Tailscale** access
- ⚠️ Do NOT expose port 8080 directly to the internet without HTTPS + additional auth

## 📡 IoT / Sensors

### Supported Sensors (direct GPIO/I2C)
| Sensor | Protocol | Use |
|--------|----------|-----|
| DHT22 | 1-Wire | Temperature & Humidity |
| BME280 | I2C | Temp, Humidity, Pressure |
| DS18B20 | 1-Wire | Waterproof Temperature |
| HC-SR04 | GPIO | Ultrasonic Distance |
| PIR HC-SR501 | GPIO | Motion Detection |
| MQ-2 | GPIO/ADC | Gas/Smoke |
| Relay Module | GPIO | Switch devices |

### ESP32/Arduino via MQTT
```
Topic format: sensors/<device_id>/<metric>
Payload: numeric value (e.g. "22.5")

Example (Arduino):
  client.publish("sensors/esp-living/temp", "22.5");
  client.publish("sensors/esp-living/humidity", "45");
```

### Arduino via USB Serial
```
Format: JSON per line at 9600 baud
Example: {"temp": 22.5, "humidity": 45}
```

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, uvicorn
- **Frontend**: Vanilla JS, xterm.js, Chart.js
- **Database**: SQLite (metrics history, sensor data)
- **IoT**: MQTT (Mosquitto), libgpiod, pyserial
- **AI**: Ollama (local LLM)
- **VPN**: Tailscale

## 📄 License

MIT — use it however you want.
