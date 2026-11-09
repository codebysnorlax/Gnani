# Installation and Setup Guide

Complete cross-platform installation and setup instructions for SAARTHI across Linux, macOS, and Windows operating systems.

---

## Table of Contents

1. [Prerequisites and System Requirements](#prerequisites-and-system-requirements)
2. [Linux Setup Guide](#linux-setup-guide)
3. [macOS Setup Guide](#macos-setup-guide)
4. [Windows Setup Guide](#windows-setup-guide)
5. [Windows Subsystem for Linux (WSL2) Setup](#windows-subsystem-for-linux-wsl2-setup)
6. [Environment Configuration (.env)](#environment-configuration-env)
7. [Database and Brand Seed Initialization](#database-and-brand-seed-initialization)
8. [Running the Application](#running-the-application)
9. [Running the Automated Test Suite](#running-the-automated-test-suite)
10. [Troubleshooting by Platform](#troubleshooting-by-platform)

---

## Prerequisites and System Requirements

Ensure the following prerequisites are met before installing:

- Operating System:
  - Linux (Ubuntu 20.04+, Debian 11+, Fedora 38+, Arch Linux)
  - macOS (macOS 12 Monterey or newer, Apple Silicon or Intel)
  - Windows (Windows 10 version 2004+ or Windows 11, 64-bit)
- Python Version: Python 3.10, 3.11, or 3.12 (Python 3.12 recommended)
- Version Control: Git 2.30+
- Telegram Account: A Telegram Bot Token obtained from [@BotFather](https://t.me/BotFather)
- Gnani.ai Platform Access: API credentials from the Gnani.ai Developer Console (https://docs.gnani.ai)
- Optional LLM API Keys: Gemini, Groq, or OpenRouter for multi-tier cascading extraction

---

## Linux Setup Guide

### 1. Install System Dependencies

#### Ubuntu / Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git build-essential ffmpeg
```

#### Fedora / RHEL:
```bash
sudo dnf install -y python3 python3-pip git gcc make ffmpeg-free
```

#### Arch Linux:
```bash
sudo pacman -Syu --needed python python-pip git base-devel ffmpeg
```

### 2. Clone the Repository
```bash
git clone https://github.com/codebysnorlax/Gnani.git
cd Gnani
```

### 3. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
python3 -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

---

## macOS Setup Guide

Supports both Apple Silicon (M1/M2/M3/M4) and Intel (x86_64) architectures.

### 1. Install Xcode Command Line Tools
```bash
xcode-select --install
```

### 2. Install Homebrew (if not already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 3. Install Python, Git, and FFmpeg via Homebrew
```bash
brew install python@3.12 git ffmpeg
```

Verify Python installation:
```bash
python3 --version
git --version
```

### 4. Clone the Repository
```bash
git clone https://github.com/codebysnorlax/Gnani.git
cd Gnani
```

### 5. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 6. Install Dependencies
```bash
python3 -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

---

## Windows Setup Guide

Compatible with Windows 10 (Build 19041+) and Windows 11 using PowerShell or Command Prompt.

### 1. Install Python 3.12
1. Download the official installer from [python.org](https://www.python.org/downloads/).
2. During installation, select the checkbox: **"Add python.exe to PATH"**.
3. Choose **"Customize installation"** and verify that `pip`, `tcl/tk`, and `py launcher` are enabled.
4. Disable the path length limit when prompted at the end of the installation.

### 2. Install Git for Windows
Using Windows Package Manager (winget):
```powershell
winget install --id Git.Git -e --source winget
```
Alternatively, download from [git-scm.com](https://git-scm.com/download/win).

### 3. Configure PowerShell Execution Policy
By default, Windows blocks PowerShell scripts like virtual environment activation. Open PowerShell as Administrator or run in current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 4. Clone the Repository
```powershell
git clone https://github.com/codebysnorlax/Gnani.git
cd Gnani
```

### 5. Create and Activate Virtual Environment

#### Using PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Using Command Prompt (cmd.exe):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

### 6. Install Dependencies
```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

*Note for Windows:* If packages requiring C-extensions (such as `reportlab` or `greenlet`) prompt for build tools, download and install the **Visual C++ Build Tools** from Microsoft: https://visualstudio.microsoft.com/visual-cpp-build-tools/

---

## Windows Subsystem for Linux (WSL2) Setup

For the best developer experience on Windows machines, running through WSL2 is highly recommended.

### 1. Enable and Install WSL2 with Ubuntu
Open PowerShell as Administrator:
```powershell
wsl --install -d Ubuntu
```
Restart your computer when prompted.

### 2. Follow Linux Setup Instructions Inside Ubuntu
Once Ubuntu opens, execute the standard Linux instructions:
```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git build-essential ffmpeg
git clone https://github.com/codebysnorlax/Gnani.git
cd Gnani
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
```

---

## Environment Configuration (.env)

Copy the sample environment file to `.env`:

### Linux / macOS:
```bash
cp .env.example .env
```

### Windows (PowerShell / CMD):
```powershell
copy .env.example .env
```

### Edit `.env` with Your Credentials:

```ini
APP_ENV=development
APP_NAME=SAARTHI
TIMEZONE=Asia/Kolkata

# Telegram Bot Configuration (Obtained from @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ

# Gnani AI Speech APIs Configuration (https://docs.gnani.ai)
GNANI_API_KEY=your_gnani_api_key_here
GNANI_STT_URL=https://api.vachana.ai/stt/v3
GNANI_TTS_URL=https://api.vachana.ai/api/v1/tts/inference

# 4-Tier Zero-Cost LLM Router Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
PRIMARY_LLM_PROVIDER=openrouter
LLM_MODEL=gemini-3.5-flash-lite
OPENROUTER_MODEL=auto

# Local SQLite Database (WAL Mode)
DATABASE_URL=sqlite+aiosqlite:///data/saarthi.db
```

---

## Database and Brand Seed Initialization

Initialize the local SQLite schema and populate the verified corporate brand directory (50+ Indian brands and Nodal Grievance Officers):

```bash
python scripts/init_db.py
python scripts/seed_brands.py
```

Expected output:
- SQLite tables created with Write-Ahead Logging (`WAL`) mode enabled.
- Corporate brand directory indexed and verified.

---

## Running the Application

Ensure the virtual environment is activated, then start the Telegram bot:

```bash
python src/saarthi/main.py
```

Alternatively, launch using the registered package entrypoint:
```bash
saarthi
```

When started, the terminal logs will confirm:
- Database connection established (`sqlite+aiosqlite`).
- Bot commands registered with Telegram API.
- Long-polling listener active for messages and voice notes.

Open Telegram, search for your bot, and send `/start`.

---

## Running the Automated Test Suite

SAARTHI includes an automated test suite covering unit calculations, statutory lookups, PII scrubbing, voice prompts, and integration workflows.

Run all tests:
```bash
pytest tests/ -v
```

Run specific test modules:
```bash
# Test statutory claim calculator
pytest tests/test_calculator.py -v

# Test deterministic legal statute registry
pytest tests/test_statutes.py -v

# Test PII scrubber
pytest tests/test_pii_scrubber.py -v

# Test brand resolution
pytest tests/test_brands.py -v

# Test end-to-end integration pipeline
pytest tests/integration/test_end_to_end.py -v
```

---

## Troubleshooting by Platform

### Linux
- **Issue: Missing audio playback or codec tools:**
  - Fix: Install FFmpeg via system package manager (`sudo apt install ffmpeg`).
- **Issue: SQLite permission denied in `data/` directory:**
  - Fix: Ensure write permissions: `chmod -R u+w data/`.

### macOS
- **Issue: `clang: error: unsupported option` during package build:**
  - Fix: Reinstall command line tools: `xcode-select --install`.
- **Issue: Architecture mismatch (x86_64 vs arm64):**
  - Fix: Ensure running under native terminal without Rosetta: `arch` should output `arm64`.

### Windows
- **Issue: `Activate.ps1 cannot be loaded because running scripts is disabled`:**
  - Fix: Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your PowerShell window.
- **Issue: `error: Microsoft Visual C++ 14.0 or greater is required`:**
  - Fix: Install the Microsoft C++ Build Tools from [visualstudio.microsoft.com](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
- **Issue: Line ending differences (CRLF vs LF):**
  - Fix: Configure Git to preserve LF: `git config --global core.autocrlf true`.

### General Network & Telegram Issues
- **Issue: `TelegramConflictError: Conflict: terminated by other getUpdates request`:**
  - Fix: Only one instance of the bot can run simultaneously using the same Telegram Bot Token. Terminate any previous background processes before starting a new session.
- **Issue: Gnani API HTTP 401 Unauthorized:**
  - Fix: Verify that `GNANI_API_KEY` in `.env` is correctly set and has active speech quota on the Gnani platform.
- **Issue: External LLM Timeout or Rate Limit:**
  - Fix: SAARTHI automatically falls back through its 4-tier cascading router (Gemini -> Groq -> OpenRouter -> Offline Regex Fallback), ensuring the system remains functional even with zero cloud LLM quota.
