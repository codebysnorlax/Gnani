# SAARTHI (pronounced saar-thee)

Voice-first Telegram assistant that converts spoken consumer grievances into formal pre-litigation legal demand notices, National Consumer Helpline (NCH 1915) filings, and public social escalation posts under the **Consumer Protection Act, 2019**, across **10 Indic languages** powered by **Gnani.ai Speech AI (Prisma v3.0 STT & Timbre v3.0 TTS)**.

---

## Core Capabilities

1. **Voice-First Grievance Intake:** Citizen speaks in their preferred language or code-mixed speech (Hindi, English, Kannada, Tamil, Telugu, Marathi, Bengali, Gujarati, Malayalam, or Punjabi).
2. **Multi-Lingual Speech Recognition:** Transcribes audio via **Gnani.ai Prisma v3.0** with Inverse Text Normalization (ITN) and script-based Indic language detection.
3. **Dynamic Context-Aware Clarification:** Employs a context-aware Response Composer grounded strictly in verified case facts. It acknowledges provided details naturally and asks one single focused clarification at a time without repeating previously answered questions.
4. **Natural Speech Synthesis:** Delivers natural voice responses using **Gnani Timbre v3.0** with strict sparse audio tag formatting (`<pauses>`, `<slow>`), eliminating artificial emotional tags and placeholder audio.
5. **PII Scrubbing:** Automatically redacts payment cards, CVVs, and Aadhaar numbers before processing or logging.
6. **Deterministic Statutory Calculation:**
   - Maps grievances deterministically to applicable provisions of CPA 2019, E-Commerce Rules 2020, RBI TAT, and DGCA Passenger Charter.
   - Computes statutory interest and damages using integer paise arithmetic.
   - Resolves brand information against a curated directory of corporate entities and nodal officers.
7. **Tri-Fold Escalation Dossier:**
   - **PDF Legal Demand Notice:** Court-ready A4 PDF generated with ReportLab and TrueType NotoSans fonts supporting the INR currency symbol and statutory disclaimer.
   - **NCH 1915 WhatsApp Filing:** Formatted complaint block under 2,000 characters with one-tap deep link to the official helpline.
   - **X Public Escalation:** Focused public escalation draft under 280 characters tagging official watchdog handles.
   - **Spoken Voice Guide:** Natural spoken walkthrough in the user's selected language.

---

## Supported Indic Languages & Voices

SAARTHI supports 10 Indian languages via Gnani Speech AI:

| Language | Code | Native Name | Verified Voice Characters |
|---|---|---|---|
| **Hindi** | `hi-IN` | हिन्दी | Shivani (Female) / Devansh (Male) / Chetana (Female) |
| **English (India)** | `en-IN` | Indian English | Shivani / Devansh / Chetana |
| **Kannada** | `kn-IN` | ಕನ್ನಡ | Shivani / Chetana |
| **Tamil** | `ta-IN` | தமிழ் | Shivani / Chetana |
| **Telugu** | `te-IN` | తెలుగు | Shivani / Chetana |
| **Marathi** | `mr-IN` | मराठी | Shivani / Chetana |
| **Bengali** | `bn-IN` | বাংলা | Shivani / Devansh |
| **Gujarati** | `gu-IN` | ગુજરાતી | Shivani / Chetana |
| **Malayalam** | `ml-IN` | മലയാളം | Shivani / Chetana |
| **Punjabi** | `pa-IN` | ਪੰਜਾਬੀ | Shivani / Devansh |

User language and voice preferences are selectable via persistent Telegram reply keyboards and persisted per user across restarts.

---

## Conversational Speech Architecture

```
                          ┌──────────────────────────┐
                          │   Citizen Voice Note     │
                          │   (10 Indic Languages)   │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │    Gnani Prisma v3.0     │
                          │   STT + Inverse Text     │
                          │   Normalization (ITN)    │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │    What I Heard Check    │
                          │   Transparent Transcript │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │    PII Scrubbing Node    │
                          │   Aadhaar, PAN, Card     │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │ Cascading Entity Intake  │
                          │ Gemini / Groq / Regex    │
                          └─────────────┬────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
            Missing Details?                         Fact Complete?
                    │                                       │
                    ▼                                       ▼
        ┌───────────────────────┐               ┌───────────────────────┐
        │  Context-Aware        │               │   Statutory Resolve   │
        │  Response Composer    │               │  CPA 2019 Claim Calc  │
        │  Single Clarification │               │  Brand Directory Map  │
        └───────────┬───────────┘               └───────────┬───────────┘
                    │                                       │
                    │ (User answers via voice/text)         ▼
                    └───────────────────────────> ┌─────────────────────┐
                                                  │ Awaiting Confirm    │
                                                  │ Case Assessment     │
                                                  └─────────┬───────────┘
                                                            │ Tap [Review & Generate]
                                                            ▼
                                                  ┌─────────────────────┐
                                                  │  Atomic Dossier Gen │
                                                  │  • PDF Legal Notice │
                                                  │  • NCH 1915 Block   │
                                                  │  • X/Twitter Post   │
                                                  │  • Voice Guidance   │
                                                  └─────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|---|---|
| **Bot Framework** | `aiogram 3.x` with input-area persistent reply keyboards |
| **Speech Processing** | `gnani-vachana` SDK (`prisma-v3.0` STT and `timbre-v3.0` TTS) |
| **Agent / Workflow** | `langgraph` state machine + `ResponseComposer` |
| **PDF Generation** | `reportlab` with bundled TrueType NotoSans fonts |
| **Database** | SQLite in WAL mode (`sqlite+aiosqlite` via SQLAlchemy 2.0) |
| **Directory Search** | `rapidfuzz` brand resolution against verified corporate directory |
| **State Persistence** | Per-user SQLite session storage surviving restarts |

---

## Prerequisites

- **Python 3.12+**
- **Telegram Bot Token** (from @BotFather)
- **Gnani.ai API Key** (from Gnani Developer Platform)
- Optional: Gemini, Groq, or OpenRouter API key for LLM fact extraction

---

## Setup & Execution

### 1. Environment Setup

```bash
git clone https://github.com/codebysnorlax/Gnani.git
cd Gnani

python3 -m venv .venv
source .venv/bin/activate

pip install -e ".[dev]"
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

Set the required environment keys:
```ini
TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
GNANI_API_KEY="your-gnani-api-key"
GEMINI_API_KEY="your-gemini-key"
```

### 3. Initialize Database & Directory

```bash
python scripts/init_db.py
python scripts/seed_brands.py
```

### 4. Run the Bot

```bash
python src/saarthi/main.py
# or via entrypoint:
saarthi
```

---

## Telegram Bot Commands

- `/start` - Initial onboarding, persistent controls, and greeting.
- `/language` - Change preferred language across 10 Indic languages.
- `/voice` - Change preferred Timbre voice character (Shivani, Devansh, Chetana).
- `/newdispute` - Clears active draft session to start a fresh grievance.
- `/mycases` - Lists past consumer dispute references.
- `/privacy` - Completely purges user records and dispute data from database.
- **Send Voice Note or Text** - Automatically triggers multi-turn context-aware intake.

---

## Data Privacy & DPDP Act 2023 Compliance

1. **Client-Side Redaction**: Sensitive personal payment data and identity identifiers are scrubbed before entity extraction.
2. **Deterministic Pre-Litigation Framing**: All financial calculations are clearly communicated as illustrative pre-litigation demand estimates under Section 35 of the Consumer Protection Act, 2019.
3. **Data Erasure**: Calling `/privacy` purges all session rows, dispute cases, and associated artifacts from SQLite storage.
4. **Resilient Session Recovery**: Durable state persistence allows users to seamlessly resume interrupted grievances after bot restarts.

---

## Testing

Run the automated test suite:

```bash
.venv/bin/pytest tests/ -v
```
