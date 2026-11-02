# Proposal

## Why

Planning train travel in India is cognitively demanding due to complex station codes, operating run-days, volatile seat availability, and multi-class fare tiers, while general-purpose AI chat tools frequently hallucinate railway facts. SAFARIQ provides a voice-enabled, Telegram-first conversational assistant that grounds all railway facts in verifiable provider data, calculates explainable recommendations deterministically, and prepares travellers for safe completion on the official IRCTC platform without ever fabricating data or attempting automated ticket booking.

## What Changes

- **Foundation & Core Architecture**: Establish clean single-language Python architecture using FastAPI, Pydantic v2, SQLite with WAL mode, and async SQLAlchemy/aiosqlite.
- **Telegram Conversational Interface**: Provide Telegram bot supporting text messages and voice notes with robust callback handling, inline keyboard navigation, and update idempotency.
- **Speech Transcription**: Integrate Gnani Prisma v3 STT REST API for Indian voice notes (Hindi, Hinglish, English) with automatic fallback to text mode upon failure or missing credentials.
- **Travel Intent & Disambiguation**: Parse natural language travel requests into typed criteria, resolve relative/yearless dates strictly in `Asia/Kolkata`, and disambiguate origin/destination stations against a curated station master.
- **Railway Provider Abstraction**: Implement `RailwayProvider` interface supporting schedule lookups, date-aware service-day validation, seat availability normalization, and fare arithmetic using `Decimal` / integer paise with strict provenance metadata (`provider_id`, `retrieved_at`, freshness).
- **Mock & Demo Architecture**: Build realistic mock railway fixtures for Bokaro-Delhi and common routes to enable comprehensive offline development and testing with explicit `DEMO DATA` banners.
- **Deterministic JourneyFit Ranking**: Score valid options against user constraints (budget, arrival deadlines, departure windows, travel duration) with transparent evidence-based explanations and What-If constraint adjustment.
- **Verified Official Booking Handoff**: Revalidate schedule, fare, and availability before handoff, alert users to any pricing/seat status changes, format a copyable journey summary, and provide a direct link to the allowlisted official IRCTC portal.
- **Persistence & State Orchestration**: Implement LangGraph stateful workflow with SQLite checkpointing and dedicated relational tables for users, trips, search sessions, quotes, and handoffs.

## Capabilities

### New Capabilities

- `travel-intent`: Natural-language text and voice transcription parsing, IST date resolution, station directory normalization, and interactive clarification workflows.
- `railway-provider`: Replaceable railway provider abstraction, service-day operating validation, seat availability status normalization, Decimal/integer paise fare calculation, and provenance metadata tracking.
- `journey-ranking`: Deterministic JourneyFit evaluation, hard constraint filtering, evidence-based ranking explanations, and conversational What-If constraint adjustments.
- `booking-handoff`: Pre-handoff revalidation, fare and seat drift detection, copyable booking summary preparation, and allowlisted official IRCTC booking portal handoff.
- `telegram-agent`: Telegram bot conversational interface, LangGraph stateful workflow orchestration, SQLite persistence, update idempotency, and session lifecycle management.

### Modified Capabilities

None. (Initial implementation)

## Impact

- **New Dependencies**: `fastapi`, `uvicorn`, `pydantic>=2.0`, `aiogram` (or `python-telegram-bot`), `langgraph`, `langgraph-checkpoint-sqlite`, `langchain`, `httpx`, `aiosqlite`, `sqlalchemy>=2.0`, `alembic`, `pytest`, `pytest-asyncio`, `respx`.
- **Infrastructure**: Local SQLite database with WAL mode enabled (`data/safariq.db`), single-process worker architecture. No Redis or external database required.
- **External Services**: Telegram Bot API, Gnani Prisma v3 REST API, third-party Railway Data API (when configured; mock provider used for demo/testing), Official IRCTC portal for external handoff.
- **Security & Privacy**: Zero storage of IRCTC credentials, passwords, OTPs, or payment details. Strict allowlisting of official IRCTC URLs. Idempotency tracking to prevent duplicate Telegram update processing.
