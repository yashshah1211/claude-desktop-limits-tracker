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
- **Verifiable**: Always verify the cryptographic checksum before running:
  ```cmd
  certutil -hashfile ClaudeLimitTracker.exe SHA256
  ```
  See [RELEASE_VERIFICATION.md](RELEASE_VERIFICATION.md) for full verification details.

### 🛠️ Option B: Run from Source
If you already have Python installed:
```bash
# Clone the repository
git clone https://github.com/yashshah1211/claude-desktop-limits-tracker.git
cd claude-desktop-limits-tracker

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

## 🔒 Security & Privacy

Please review our security disclosures and privacy architecture before using this tool:

### 1. Local Credential Access & Network Confinement
- **Local Acquisition**: This tool reads the user's Claude.ai session key locally, either by scanning `claude.exe`'s own process memory (`ReadProcessMemory`) or decrypting the local widget configuration via Windows DPAPI (`CryptUnprotectData`).
- **Strict Outbound Host Allowlist**: The session key is **never** transmitted anywhere except Claude.ai's official domain (`https://claude.ai/api/...`). Outbound network calls are strictly restricted by code-level host validation (`parsed.hostname == "claude.ai"` and `parsed.scheme == "https"`); any request targeting an unauthorized host or subdomain (e.g. `https://claude.ai.attacker.com`) is blocked immediately.
- **Zero Third-Party Telemetry**: There is zero tracking, external analytics, remote error reporting, or third-party servers. All processing is 100% local.
- **Localhost-Only Web Binding**: The local web dashboard server binds strictly to `127.0.0.1` (localhost only), preventing exposure to other devices on the same local network (LAN).
- **No Credential Caching or Logging**: The on-disk history cache (`plan-usage-history.json`) and runtime status payloads store only usage percentages and timestamps—never the raw session key. All error messages, logs, and exception strings automatically scrub and mask session tokens before display.

### 2. Unofficial API & Non-Affiliation
- **Undocumented Endpoint**: This tool queries an **unofficial, undocumented Claude.ai internal API endpoint** (`https://claude.ai/api/organizations/{org_id}/usage`) that Anthropic does not publish, document, or support. This endpoint may change, require different authentication, or break at any time without notice.
- **Non-Affiliation**: This project is an independent community utility and is **not affiliated with, endorsed by, sponsored by, or associated with Anthropic, PBC**.

### 3. Terms of Service Notice
- **Terms of Service Compliance**: This project has not been reviewed for compliance with Anthropic's Consumer Terms of Service. Users should read those terms themselves before using this tool and make their own determination.

### 4. Antivirus & Windows Defender Heuristics (False Positives)
- **Heuristic Detection**: Because this utility reads memory from another running process (`claude.exe` via Windows `ReadProcessMemory`) and handles authentication credentials in memory, Windows Defender or third-party antivirus software may flag the executable with generic heuristic labels (such as `Trojan:Win32/Wacatac` or `Heur.BZC`).
- **Verifiable Integrity**: This is a known heuristic false positive resulting from memory inspection patterns, not evidence of malicious activity. Rather than asking users to simply "trust us," this project provides complete transparency and verification:
  - The entire source code is open, auditable, and cleanly structured.
  - Release binaries are compiled automatically in isolated GitHub Actions cloud runners from tagged commits.
  - You can verify the official SHA256 checksum of your downloaded binary before executing it (see [RELEASE_VERIFICATION.md](RELEASE_VERIFICATION.md)).
  - You can inspect the [GitHub Actions build workflow](.github/workflows/build-release.yml) or compile the binary yourself from source.

### 5. Workstation Security Recommendation
- **Shared / Enterprise Machine Warning**: We recommend that users **do not run this tool on shared, public, or employer-monitored computers** that they do not fully control. A session key grants account-level access to Claude.ai; handling credentials or running memory scanners in shared or monitored environments carries inherent risk.

---

## 🔍 Release Verification

To verify that your downloaded `ClaudeLimitTracker.exe` has not been tampered with and matches the official GitHub Actions build:

```cmd
certutil -hashfile ClaudeLimitTracker.exe SHA256
```

Compare the resulting 64-character hash against the `ClaudeLimitTracker.exe.sha256` asset attached to the release. See the [Release Verification Guide](RELEASE_VERIFICATION.md) for full instructions.

---

## 📂 Project Structure

```
├── gui.py                  # Standalone Windows GUI (High-DPI Tkinter Canvas)
├── cli.py                  # Terminal CLI with ANSI color bars & live watch mode
├── web_server.py           # Local HTTP server providing JSON API & dashboard (127.0.0.1)
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
├── RELEASE_VERIFICATION.md # Step-by-step SHA256 verification instructions
└── .github/workflows/
    └── build-release.yml   # Automated GitHub Actions release builder & checksum generator
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

## ⚠️ Disclaimer

This software is provided "AS IS", without warranty of any kind, express or implied. Use at your own risk. This project is an independent, open-source community tool and is **NOT affiliated with, endorsed by, sponsored by, or associated with Anthropic, PBC**. "Claude" and "Anthropic" are trademarks of Anthropic, PBC. The authors and contributors assume no liability or responsibility for account status, service interruptions, API changes, data issues, or any damages arising from the use of this software.

---

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).
