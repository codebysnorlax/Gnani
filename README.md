# ConsumerDost (`उपभोक्ता दोस्त`)

Voice-first Telegram bot that converts spoken consumer grievances (Hindi, Hinglish, English) into formal pre-litigation legal demand notices, National Consumer Helpline (NCH 1915) filings, and social escalation posts under the **Consumer Protection Act, 2019**.

---

## What It Does

1. **Voice Grievance Intake:** User sends a voice note describing an issue (e.g. defective phone delivered by Flipkart, refund denied by airline, failed UPI transaction).
2. **Speech-to-Text:** Transcribes audio via **Gnani.ai Prisma v3.0** with inverse text normalization (numbers converted to currency/order formats).
3. **PII Scrubbing:** Automatically redacts 16-digit payment cards, CVVs, and 12-digit Aadhaar IDs before processing. Order IDs and UTRs are preserved.
4. **Deterministic Statutory Calculation:**
   - Maps grievance to exact legal provisions (CPA 2019, E-Commerce Rules 2020, RBI TAT, DGCA Charter).
   - Computes claims using exact integer paise arithmetic (Principal + 9% p.a. interest + statutory penalties + tiered harassment damages).
   - Resolves brand against a 50-brand directory (corporate name, registered office, nodal grievance email).
5. **Generates Tri-Fold Escalation Dossier:**
   - **PDF Legal Demand Notice:** Formatted A4 PDF (ReportLab + TrueType NotoSans fonts with valid `₹` symbol, Section 35 CPA disclaimer, 15-day notice window).
   - **NCH 1915 WhatsApp Filing:** Formatted <2000 character complaint block + 1-tap WhatsApp link (`wa.me/918860005372`).
   - **X / Twitter Post:** Pre-composed <280 character tweet tagging brand handle, `@jagograhakjago`, and `@consaff_india` + click-to-tweet URL.
   - **Voice Note Reply:** Synthesizes Hindi audio summary using **Gnani.ai Timbre v2.5** TTS and sends it back to Telegram.

---

## Tech Stack

| Component | Technology |
|---|---|
| **Bot Framework** | `aiogram 3.x` (Telegram Bot API) |
| **Speech STT & TTS** | `gnani-vachana` official SDK (`prisma-v3.0` STT, `timbre-v2.5` TTS) |
| **Agent / Workflow** | `langgraph` state machine + cascading LLM router (Gemini / Groq / OpenRouter / pure-Python regex fallback) |
| **PDF Engine** | `reportlab` with bundled Unicode TrueType fonts (`assets/fonts/NotoSans-*.ttf`) |
| **Database** | SQLite with WAL mode enabled (`sqlite+aiosqlite` via SQLAlchemy 2.0) |
| **Brand Lookup** | `rapidfuzz` fuzzy matching against `data/brands.json` |

---

## Prerequisites

- **Python 3.12+**
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- **Gnani.ai API Key** (from [Gnani Developer Platform](https://docs.gnani.ai/))
- Optional: Gemini, Groq, or OpenRouter API key for LLM extraction (offline regex fallback works without any LLM key).

---

## Setup & Quickstart

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/codebysnorlax/Gnani.git
cd Gnani

# Create virtual environment and activate
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
GNANI_API_KEY="your-gnani-api-key"

# Optional: LLM keys for advanced parsing (system falls back to regex if omitted)
GEMINI_API_KEY=""
GROQ_API_KEY=""
```

### 3. Initialize Database & Seed Brands

```bash
python scripts/init_db.py
python scripts/seed_brands.py
```

### 4. Run the Bot

```bash
python src/consumerdost/main.py
```

Open Telegram, search for your bot, and send `/start`.

---

## Bot Commands

- `/start` — Welcome message, language selection, and guide on how to report a dispute.
- `/cases` — View all your active and resolved dispute cases.
- `/privacy` — GDPR / DPDP 2023 compliant command to permanently purge your data and cases.
- **Send Voice Note or Text** — Any voice note or text message triggers grievance parsing and assessment.

---

## Project Structure

```text
├── assets/
│   └── fonts/               # Bundled NotoSans TTF fonts for clean ₹ symbol rendering
├── data/
│   └── brands.json          # Master directory of 50 Indian brands with nodal emails
├── scripts/
│   ├── init_db.py           # Database table initialization
│   └── seed_brands.py       # Seeds brands.json into SQLite brand directory
├── src/
│   └── consumerdost/
│       ├── agent/           # LangGraph workflow, 4-tier LLM router & regex fallback
│       ├── database/        # Async SQLAlchemy engine (WAL mode), models, repository
│       ├── documents/       # PDF generator, NCH 1915 WhatsApp & Twitter formatters
│       ├── domain/          # Statutory registry (CPA 2019), integer paise calculator, brand lookup
│       ├── security/        # PII scrubber (redacts cards, CVVs, Aadhaar IDs)
│       ├── speech/          # Gnani.ai STT (Prisma v3.0) & TTS (Timbre v2.5) integrations
│       ├── telegram/        # aiogram bot, handlers, keyboards, formatters
│       ├── config.py        # Pydantic Settings configuration
│       └── main.py          # Application entrypoint
└── tests/
    ├── integration/         # End-to-end pipeline, Gnani API, LangGraph, and PDF tests
    └── unit/                # PII scrubber, calculator, statutory rules, brand lookup tests
```

---

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

All 36 unit and integration tests run offline or against live fixtures.
