# Proposal

## Why

Millions of Indian consumers lose money daily to micro- and mid-sized disputes across e-commerce, quick-commerce, airlines, telecom, and digital payments, but 95% abandon valid claims under INR 25,000 due to corporate chatbot stonewalling, legal drafting intimidation, and unaffordable lawyer fees. ConsumerDost democratizes pre-litigation consumer rights in India by providing a voice-first conversational legal copilot that turns 30-second colloquial grievances in Hindi, Hinglish, or English into structured, legally grounded escalation packages—including formal Legal Demand Notices (PDF), National Consumer Helpline (NCH 1915) filings, and executive social posts—in under 4 seconds.

## What Changes

- **Foundation & Core Architecture**: Build a single-language Python 3.12+ backend running on SQLite with Write-Ahead Logging (WAL mode), aiosqlite, and SQLAlchemy 2.0.
- **Telegram Conversational Interface**: Deploy an aiogram 3.x bot accepting voice notes (.ogg/.oga up to 60 seconds) and text messages, featuring update deduplication, inline confirmation cards, and hard-deletion privacy controls (/privacy).
- **Gnani Speech Integration**: Connect Gnani Prisma v3.0 REST STT (indic-auto, hi-IN, en-IN) for multilingual voice transcription and Gnani Timbre REST TTS for 15-second native audio summaries, backed by graceful text fallbacks.
- **Pre-LLM PII Sanitizer**: Implement a deterministic regex scrubber (scrub_sensitive_pii) that redacts 12-digit government IDs, 16-digit payment cards, CVVs, and PINs before persistence or model invocation.
- **4-Tier Zero-Cost LLM Extractor**: Implement an automated cascading extractor (Tier 1 Groq/Gemini -> Tier 2 OpenRouter -> Tier 3 Golden Demo Fixture Cache -> Tier 4 Deterministic Regex & Keyword Fallback) to guarantee 100% demo uptime with zero cost and zero runtime failure risk.
- **Curated 50-Brand Nodal Directory**: Embed a verified directory of top Indian brands with RapidFuzz alias matching to resolve legal corporate entities, registered office addresses, statutory Nodal Grievance emails, and social handles.
- **Deterministic Legal & Financial Engine**: Map dispute categories strictly against the Consumer Protection Act, 2019 (Sections 2(10), 2(11), 2(47)), E-Commerce Rules 2020, CCPA Dark Patterns Guidelines 2023, and sectoral circulars (RBI TAT, DGCA Passenger Charter), calculating claims in integer paise with 9% p.a. equitable interest and tiered mental agony damages.
- **Unicode-Safe Tri-Fold Document Generation**: Render formal English Legal Demand Notices in A4 PDF using ReportLab with bundled NotoSans TrueType fonts for native Rupee symbol (INR / U+20B9) support, accompanied by NCH 1915 WhatsApp/web blocks and X/Twitter escalation drafts.
- **Stateful LangGraph Workflow**: Coordinate multi-turn clarification, brand resolution, case confirmation, and document delivery with SQLite checkpoint persistence.

## Capabilities

### New Capabilities
- `speech-intake`: Handles Telegram audio download, audio format normalization, Gnani Prisma v3.0 STT transcription, and Gnani Timbre TTS speech synthesis with bounded timeouts and text fallback.
- `pii-protection`: Deterministic regex sanitization redacting government IDs, payment cards, CVVs, and PINs prior to storage or LLM processing.
- `grievance-extraction`: 4-tier cascading extractor that extracts brands, categories, dispute types, amounts, dates, and order identifiers across cloud LLMs, free routers, and offline regex fallbacks.
- `brand-directory`: RapidFuzz resolution of colloquial company queries against a verified 50-brand master database containing corporate addresses, nodal emails, and social handles.
- `statutory-dispute-engine`: Deterministic mapping of grievances to Consumer Protection Act 2019 provisions and integer-paise financial math for equitable interest, regulatory penalties, and tiered damages.
- `escalation-dossier`: Generation of Unicode-safe ReportLab legal notice PDFs with Indian legal typography, NCH 1915 dossiers with WhatsApp links, and X escalation threads.
- `telegram-workflow`: Stateful conversational orchestration via aiogram 3.x and LangGraph with SQLite WAL persistence, idempotency tracking, and interactive case confirmation cards.

### Modified Capabilities
None. (Greenfield specification)

## Impact

- **New Dependencies**: `aiogram>=3.10.0`, `langgraph>=0.2.0`, `langgraph-checkpoint-sqlite>=2.0.0`, `reportlab>=4.2.0`, `rapidfuzz>=3.8.0`, `httpx>=0.27.0`, `pydantic>=2.7.0`, `pydantic-settings>=2.2.0`, `sqlalchemy>=2.0.0`, `aiosqlite>=0.20.0`, `google-genai>=0.1.0`, `groq>=0.11.0`, `pypdf>=4.2.0`, `pytest>=8.2.0`, `pytest-asyncio>=0.23.0`, `respx>=0.21.0`.
- **Infrastructure**: Local SQLite database with WAL mode enabled (`data/consumerdost.db`), bundled TrueType fonts in `assets/fonts/`, and single-process async bot runner.
- **External Services**: Telegram Bot API, Gnani AI Speech APIs (`https://api.vachana.ai/stt/v3`, `https://api.vachana.ai/api/v1/tts/inference`), Google AI Studio / Groq Cloud / OpenRouter APIs.
- **Security & Compliance**: Strict self-representation legal disclaimers under Section 35 of CPA 2019, zero storage of banking/identity credentials, and user data purge via `/privacy`.
