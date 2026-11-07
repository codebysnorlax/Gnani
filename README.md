# ConsumerDost (`उपभोक्ता दोस्त`)

Voice-first Telegram bot that converts spoken consumer grievances into formal pre-litigation legal demand notices, National Consumer Helpline (NCH 1915) filings, and social escalation posts under the **Consumer Protection Act, 2019**, across **10 Indic languages** powered by **Gnani.ai Speech AI (Prisma v3.0 STT & Timbre v3.0 TTS)**.

---

## What It Does

1. **Voice-First Grievance Intake:** Citizen speaks in their native tongue or code-mixed speech (e.g. Hindi, Kannada, Tamil, Telugu, Marathi, Bengali, Gujarati, Punjabi, Malayalam, or English).
2. **Multi-Lingual Speech-to-Text:** Transcribes audio via **Gnani.ai Prisma v3.0** with Inverse Text Normalization (ITN) and script-based Indic language auto-detection.
3. **Voice-First AI Instructions:** Rather than wall-of-text prompts, ConsumerDost speaks back to the user at every turn (Onboarding, Clarifications, and Assessment Walkthrough) using **Gnani Timbre v3.0** expressive speech synthesis.
4. **13 Inline Expressive Audio Tags:** Injects Gnani Timbre v3.0 non-verbal cues (`<sigh>`, `<pauses>`, `<excited>`, `<whispers>`, `<slow>`, `<giggle>`, `<coughs>`, `<exhales>`, `<laugh>`, `<shouting>`, `<sniffles>`, `<yawns>`, `<clears throat>`) to convey realistic human empathy, patience, and reassurance for distressed consumers.
5. **PII Scrubbing:** Automatically redacts 16-digit payment cards, CVVs, and 12-digit Aadhaar IDs before processing. Order IDs and UTRs are preserved.
6. **Deterministic Statutory Calculation:**
   - Maps grievance to exact legal provisions (CPA 2019, E-Commerce Rules 2020, RBI TAT, DGCA Charter).
   - Computes claims using exact integer paise arithmetic (Principal + 9% p.a. interest + statutory penalties + tiered harassment damages).
   - Resolves brand against a 50-brand directory (corporate name, registered office, nodal grievance email).
7. **Tri-Fold Escalation Dossier:**
   - **PDF Legal Demand Notice:** Formatted A4 PDF (ReportLab + TrueType NotoSans fonts with valid `₹` symbol, Section 35 CPA disclaimer, 15-day notice window).
   - **NCH 1915 WhatsApp Filing:** Formatted <2000 character complaint block + 1-tap WhatsApp link (`wa.me/918860005372`).
   - **X / Twitter Post:** Pre-composed <280 character tweet tagging brand handle, `@jagograhakjago`, and `@consaff_india` + click-to-tweet URL.
   - **Timbre v3.0 Spoken Guide:** Synthesizes an empathetic audio action walkthrough in the user's preferred Indic language.

---

## Supported Indic Languages & Voices

Every Timbre v3.0 voice speaks all 10 supported Indic languages:

| Language | Code | Native Name | Default Persona Voice |
|---|---|---|---|
| **Hindi** | `hi-IN` | हिन्दी | Shivani (Warm, Empathetic) |
| **English (India)** | `en-IN` | Indian English | Shivani / Devansh (Conversational) |
| **Kannada** | `kn-IN` | ಕನ್ನಡ | Shivani / Chetana (Empathetic Care) |
| **Tamil** | `ta-IN` | தமிழ் | Shivani / Kalpana (Reassuring) |
| **Telugu** | `te-IN` | తెలుగు | Shivani / Chetana |
| **Marathi** | `mr-IN` | मराठी | Shivani / Kalpana |
| **Bengali** | `bn-IN` | বাংলা | Shivani / Devansh |
| **Gujarati** | `gu-IN` | ગુજરાતી | Shivani / Chetana |
| **Malayalam** | `ml-IN` | മലയാളം | Shivani / Kalpana |
| **Punjabi** | `pa-IN` | ਪੰਜਾਬੀ | Shivani / Shubham (Energetic) |

---

## Timbre v3.0 Audio Tags Catalog

ConsumerDost utilizes all 13 supported lower-case audio tags from the Gnani documentation:

| Tag | Category | Effect & Bot Usage |
|---|---|---|
| `<pauses>` | Silence | Inserts non-spoken silence between instructional steps |
| `<sigh>` | Breath | Expresses audible empathy when acknowledging seller misconduct |
| `<excited>` | Vocal | Energetic, positive delivery for claim resolution & greeting |
| `<whispers>` | Vocal | Soft, confidential delivery when asking for missing Order ID/name |
| `<slow>` | Pacing | Deliberate, clear delivery for legal terms and amounts |
| `<giggle>` / `<laugh>` | Laughter | Warm, conversational rapport |
| `<coughs>` / `<clears throat>` | Breath | Natural human vocal pauses |
| `<exhales>` / `<sniffles>` / `<yawns>` | Breath | Emotional realism |
| `<shouting>` | Vocal | Urgent statutory deadline notice |

---

## Tech Stack

| Component | Technology |
|---|---|
| **Bot Framework** | `aiogram 3.x` (Telegram Bot API) with `ChatAction.RECORD_VOICE` |
| **Speech STT & TTS** | `gnani-vachana` official SDK (`prisma-v3.0` STT, `timbre-v3.0` TTS with Audio Tags) |
| **Agent / Workflow** | `langgraph` state machine + `VoicePromptComposer` + cascading LLM router |
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

- `/start` — Spoken audio greeting (Timbre v3.0), language selection, and guide on how to report a dispute.
- `/language` — 1-tap language switcher across all 10 Indic languages with audio confirmation.
- `/newdispute` — Clears active session to file a fresh grievance.
- `/mycases` — View all your active and resolved dispute cases.
- `/privacy` — GDPR / DPDP 2023 compliant command to permanently purge your data and cases.
- **Send Voice Note or Text** — Any voice note or text message triggers grievance parsing, voice clarification, and assessment.

---

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

All 64 unit and integration tests run offline or against live fixtures with 100% pass rate.
