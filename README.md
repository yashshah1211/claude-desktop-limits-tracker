# ✦ Claude.ai Limits Tracker for Windows

[![License: MIT](https://img.shields.io/badge/License-MIT-coral.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue.svg)](https://microsoft.com/windows)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Local-emerald.svg)](#privacy--security)
[![Release](https://img.shields.io/badge/Download-Standalone%20.exe-da7756.svg)](#-quick-start-no-install-needed)

A dedicated Windows monitoring tool that displays your **Claude.ai limits left** in real-time. Designed specifically for users of the official **Claude Desktop App** on Windows.

Tracks both essential limits:
1. **Current Session 5-Hour Limit**: Live `% left`, `% used`, warning ring gauges, and second-by-second countdown to the exact reset moment (e.g. `Out of free messages until 2:10 AM`).
2. **Weekly (7-Day) Quota**: Weekly percentage remaining, weekly reset date/time, and model-specific quotas (Sonnet, Opus).

---

## ⚡ Quick Start (No Install Needed)

### 📥 Option A: Standalone Executable (Recommended)
Download the latest **`ClaudeLimitTracker.exe`** from the **[Releases](../../releases)** tab.
- **Single file**: Just double-click to run.
- **Zero dependencies**: No Python or Node.js required.
- **Portable**: Keep it anywhere or pin it to your Windows Taskbar.

### 🛠️ Option B: Run from Source
If you already have Python installed:
```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/claude-limits-tracker.git
cd claude-limits-tracker

# Install lightweight dependencies
pip install requests psutil cryptography

# Launch native Windows Desktop GUI
python gui.py
```
Or double-click **`start_gui.bat`** directly.

---

## ✨ Features

- **Zero-Config Detection**: Automatically detects running `claude.exe` desktop processes and active sessions. No manual copying or pasting of session cookies needed.
- **Dual Visual Meters**: High-DPI circular progress rings color-coded by remaining health:
  - 🟢 **Healthy** (> 40% buffer)
  - 🟡 **Moderate** (15% – 40%)
  - 🔴 **Low / Cooldown Active** (< 15% or hit limit)
- **Real-Time Countdown**: Second-by-second live countdown to your exact reset time.
- **Free Tier Cooldown Support**: Detects Claude Free message limits and displays exact recovery timestamps (e.g., `Out of free messages until 2:10 AM`).
- **Claude Desktop History Sync**: Reads Claude Desktop's local `plan-usage-history.json` to graph past usage peaks and cooldown periods.
- **Always on Top (`📌 Pin on Top`)**: Float the widget over your workspace or IDE while you work.
- **Multiple Views**:
  - **Native Windows GUI** (`gui.py` / `start_gui.bat`)
  - **Modern Web Dashboard** (`web_server.py` / `start_web.bat`)
  - **Terminal CLI with Live Watch** (`cli.py --watch` / `start_cli.bat`)

---

## 🔒 Privacy & Security

Users worldwide care about token security—and so do we:
- **100% Local**: All processing is strictly on your machine.
- **No Third-Party Telemetry**: Your session token and usage stats are **never** sent to any external server or analytics service.
- **Direct Anthropic Connection**: Requests are made solely and directly to `https://claude.ai/api/...` to read your account quota.
- **Open Source**: The code is completely transparent and verifiable.

---

## 📂 Project Structure

```
├── gui.py                  # Standalone Windows GUI (High-DPI Tkinter Canvas)
├── cli.py                  # Terminal CLI with ANSI color bars & live watch mode
├── web_server.py           # Local HTTP server providing JSON API & dashboard
├── start.bat               # Interactive Windows master launcher
├── start_gui.bat           # 1-click Windows GUI launcher
├── start_web.bat           # 1-click Web Dashboard launcher
├── start_cli.bat           # 1-click Terminal CLI launcher
├── assets/                 # App icons & branding
│   └── icon.ico
├── src/
│   ├── claude_client.py    # Core process sensor, LevelDB reader & Claude API client
│   └── main.js             # Electron application entry point
├── web/
│   ├── index.html          # Web dashboard structure
│   ├── style.css           # Modern dark-mode glassmorphism styling
│   └── app.js              # Real-time gauge animation & countdown engine
└── .github/workflows/
    └── build-release.yml   # GitHub Actions automated release compiler
```

---

## 🔨 Building the `.exe` Yourself

To build your own single-file `.exe` using PyInstaller:

```bash
# Using uv (ultra-fast)
uv tool run --with requests --with psutil --with cryptography pyinstaller --onefile --noconsole --name "ClaudeLimitTracker" --icon "assets/icon.ico" --add-data "assets;assets" --add-data "src;src" gui.py

# Or using standard pip
pip install pyinstaller requests psutil cryptography
pyinstaller --onefile --noconsole --name "ClaudeLimitTracker" --icon "assets/icon.ico" --add-data "assets;assets" --add-data "src;src" gui.py
```
The output file will be generated in `dist/ClaudeLimitTracker.exe`.

---

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome! Feel free to open an issue or submit a pull request.

---

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).
