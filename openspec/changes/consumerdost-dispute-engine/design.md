# Design

## Context

See `proposal.md` for background and motivation. The system operates under constraints typical of live hackathon demonstrations and Indian consumer disputes:
- Multilingual and colloquial voice/text input (Hindi, Hinglish, English) from everyday consumers.
- Unreliable third-party API availability, rate limits, or network degradation at presentation venues.
- Strict legal requirements: outputs must adhere to the Consumer Protection Act, 2019 without hallucinating statutory provisions or miscalculating financial claims.
- Zero external infrastructure overhead: all persistence, routing, and document generation must run within a single lightweight Python 3.12+ process without requiring Redis, Docker daemon, or paid database clusters.

## Goals / Non-Goals

**Goals:**
- Provide sub-4-second end-to-end processing from Telegram voice note intake to downloadable legal escalation package.
- Guarantee 100% demo uptime and extraction capability through a 4-tier fallback hierarchy (Cloud LLM -> Free Router -> Demo Fixtures -> Deterministic Regex).
- Eliminate floating-point rounding errors in financial claim generation by enforcing integer-paise calculations across all claim items, interest rates, and damages.
- Generate valid, visually formal A4 Legal Demand Notice PDFs with embedded TrueType fonts ensuring native Rupee currency symbol (INR / U+20B9) rendering.
- Preserve zero-trust data privacy by redacting high-risk PII (Aadhaar, PAN, card numbers, CVVs, PINs) before storage or external API invocation.

**Non-Goals:**
- Automated court e-filing or direct submission to state/district consumer commissions (acts strictly as a pre-litigation self-representation notice generator under Section 35 CPA 2019).
- Automated live debit card chargeback initiation or direct bank account debits.
- Real-time phone call voice agent capabilities (out of scope; asynchronous voice notes via Telegram and Gnani REST APIs are targeted).
- Multi-tenant enterprise legal department management or lawyer collaboration portal.

## Decisions

### Decision 1: Unified Async Python Architecture with SQLite WAL and LangGraph

- **Choice**: Implement an asynchronous Python 3.12+ architecture utilizing `aiogram 3.x` for Telegram bot handling, `LangGraph` with `aiosqlite` for stateful workflow orchestration, and SQLite in Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) mode.
- **Rationale**: Eliminates multi-service operational overhead (e.g., Celery, Redis, separate worker containers). SQLite WAL supports concurrent readers with single-writer safety and sub-millisecond query latency, satisfying hackathon deployment simplicity and zero cost.
- **Alternatives Considered**:
  - *PostgreSQL + Redis + Celery*: Excessive resource requirements for a single-node Telegram bot and hackathon demonstration.
  - *FastAPI + Webhook + In-Memory State*: In-memory state is lost on process restarts; webhook requires public HTTPS tunneling (e.g. ngrok), whereas Telegram long-polling with SQLite persistence allows immediate local and cloud execution.

### Decision 2: 4-Tier Cascading Extractor with Deterministic Regex Fallback

- **Choice**: Implement an extraction hierarchy:
  1. *Tier 1*: Primary Cloud LLM (`groq/llama-3.3-70b-versatile` or `gemini-2.5-flash`).
  2. *Tier 2*: Free Cloud Router (`openrouter.ai` free endpoints).
  3. *Tier 3*: Golden Demo Fixture Cache (hash/keyword match returning verified JSON in < 50ms).
  4. *Tier 4*: Deterministic Regex & Keyword Fallback (`rapidfuzz` brand resolution + regex amount/date extraction).
- **Rationale**: Public LLM APIs regularly encounter rate limits (HTTP 429), expired tokens, or network latency during evaluations. The 4-tier model guarantees that extraction never crashes and always produces a structured grievance object.
- **Alternatives Considered**:
  - *Direct single-provider LLM call*: Highly vulnerable to API downtime, rate limits, or connectivity issues.
  - *Local SLM (e.g. Ollama Llama 3 8B)*: Requires GPU or high memory (4GB+ VRAM), incompatible with lightweight CPU-only laptops or free-tier cloud VMs.

### Decision 3: Deterministic Statutory Mapping and Integer-Paise Math Core

- **Choice**: Separate legal statutory mapping and arithmetic completely from the LLM. The LLM or regex tier only extracts factual slots (Brand, Amount, Date, Order ID, Category, Summary). The statutory engine deterministically assigns CPA 2019 sections (2(10), 2(11), 2(47), E-Commerce Rules 2020) and computes claims strictly in integer paise (`amount_paise = int(round(amount_inr * 100))`).
- **Rationale**: LLMs are notoriously prone to arithmetic hallucinations and fabricating legal section numbers. Deterministic code guarantees that 9% p.a. simple interest and tiered damages are legally consistent and mathematically precise.
- **Alternatives Considered**:
  - *LLM Prompt-Based Calculation and Legal Drafting*: LLMs routinely produce floating-point errors, incorrect interest accruals, or hallucinate non-existent statutory subsections.

### Decision 4: ReportLab PDF Engine with Bundled TrueType Fonts

- **Choice**: Use Python `reportlab` with explicitly registered Google NotoSans TrueType fonts (`NotoSans-Regular.ttf`, `NotoSans-Bold.ttf`) stored in `assets/fonts/`.
- **Rationale**: Standard PDF standard 14 fonts (Helvetica, Times) do not include the Indian Rupee symbol (`U+20B9` / `₹`) and cause missing glyph boxes or black rectangles. Bundled TrueType fonts guarantee correct currency rendering, deterministic pagination, and professional layout without system font dependencies.
- **Alternatives Considered**:
  - *Weasyprint (HTML to PDF)*: Requires heavy system C-libraries (Pango, Cairo, GDK-Pixbuf), complicating environment setup on various developer machines.
  - *Headless Chrome (Puppeteer / Playwright)*: Extreme memory footprint (hundreds of MBs) and slow execution (several seconds per PDF).

### Decision 5: Pre-LLM PII Redaction Pipeline

- **Choice**: Execute a deterministic regex scrubber (`scrub_sensitive_pii`) on raw consumer input before database persistence or passing text to LLM providers. Redacts 12-digit Aadhaar patterns, 10-digit PAN alphanumeric patterns, 16-digit credit/debit card numbers, CVVs, and banking PINs.
- **Rationale**: Prevents accidental transmission of sensitive Indian consumer financial credentials to external cloud LLM APIs, adhering to the Digital Personal Data Protection Act, 2023 (DPDP Act).
- **Alternatives Considered**:
  - *Post-processing redaction*: Fails to protect data sent over the wire to third-party model inference endpoints.
  - *LLM-based PII masking*: Introduces latency, token costs, and potential leakage if the prompt injection bypasses redaction.

### Decision 6: Hybrid Speech Intake with Text Fallback

- **Choice**: Integrate Gnani Prisma v3.0 REST STT (`indic-auto`, `hi-IN`, `en-IN`) for voice note transcription and Gnani Timbre REST TTS for Hindi/English audio summaries. Wrap all Gnani calls in bounded timeouts (5.0s STT, 3.0s TTS) with automatic fallback to text transcription messages or silent summary delivery.
- **Rationale**: Consumers in Tier 2/3 Indian cities prefer voice notes over typing long grievances. Bounded timeouts ensure that temporary speech service delays never freeze the Telegram conversation.
- **Alternatives Considered**:
  - *OpenAI Whisper API*: Higher latency, lacks native Indian accent/vernacular optimization compared to Gnani Indic models.
  - *Telegram Voice-to-Text (Telegram Premium)*: Available only to paying Telegram users and inaccessible via standard Bot API for free bot users.

## Risks / Trade-offs

- **[Risk] Telegram Voice Note Format (.ogg Opus) Incompatibility**: Telegram voice notes are sent as OGG containers encoded with Opus audio, which some speech REST endpoints reject without explicit WAV/MP3 conversion.
  - *Mitigation*: Bundle lightweight in-memory format normalization via `soundfile` or `ffmpeg` if required, or submit directly using Gnani-supported audio encodings.

- **[Risk] Hallucinated or Misspelled Merchant Names**: Consumers frequently use informal merchant names (e.g. "Blinkit", "Zomato", "swiggy instamart").
  - *Mitigation*: The `brand-directory` module uses RapidFuzz token sorting ratio with an 80% threshold against 50 canonical brands and their registered aliases. If unlisted, a structured fallback mode captures the raw brand name and provides statutory defaults.

- **[Risk] High API Latency During Live Pitch**: Third-party speech and LLM endpoints may stall due to conference Wi-Fi latency.
  - *Mitigation*: Pre-load verified test audio clips and sample prompt fixtures in `data/demo_fixtures/`. When `DEMO_MODE=true` or when fixture hashes match, extraction completes in under 50ms offline.

- **[Risk] Rate Limits on Free LLM Tiers**: Groq or Gemini Free tiers may return HTTP 429 after 15 requests per minute.
  - *Mitigation*: Automatic cascading instantly falls back to OpenRouter free models, and subsequently to Tier 4 deterministic regex parsing without alerting or blocking the user.

## Migration Plan

1. **Environment Configuration**: Set environment variables in `.env` (`TELEGRAM_BOT_TOKEN`, `GNANI_API_KEY`, `GNANI_ACCESS_TOKEN`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `DEMO_MODE`).
2. **Directory & Asset Initialization**: Verify `assets/fonts/` contains `NotoSans-Regular.ttf` and `NotoSans-Bold.ttf`.
3. **Database Bootstrap**: Run async database initialization script ensuring SQLite WAL mode is active and schema tables (`users`, `disputes`, `checkpoints`) are created.
4. **Offline Validation**: Run unit test suite covering PII scrubbing, 4-tier extractor fallbacks, integer-paise financial calculations, and PDF generation.
