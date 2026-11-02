# Tasks

## 1. Phase 0 — Project Skeleton, Environment & Foundation

- [ ] 1.1 Create project repository structure (`src/safariq/`, `tests/`, `data/fixtures/`, `docs/`, `scripts/`) matching PRD Section 17, and verify directory tree exists.
- [ ] 1.2 Create `pyproject.toml` with dependencies (`fastapi`, `uvicorn`, `pydantic>=2.0`, `aiogram`, `langgraph`, `langgraph-checkpoint-sqlite`, `langchain`, `httpx`, `aiosqlite`, `sqlalchemy>=2.0`, `alembic`, `pytest`, `pytest-asyncio`, `respx`) and verify packaging configuration is valid.
- [ ] 1.3 Create `.env.example` and validated Pydantic settings module (`src/safariq/config.py`) enforcing `DEMO_MODE=true` default and verifying configuration loads correctly.
- [ ] 1.4 Create `docs/INTEGRATION_BLOCKERS.md` and `docs/ARCHITECTURE.md` documenting railway API provider terms, Gnani scopes, deployment modes, and verify docs render accurately.
- [ ] 1.5 Create basic FastAPI application lifecycle (`src/safariq/main.py`) with `/health` endpoint and verify HTTP 200 response via test.

## 2. Phase 1 — Contracts & Deterministic Domain Logic

- [ ] 2.1 Implement core enums and Pydantic models (`src/safariq/domain/enums.py` and `models.py`) covering stations, trains, availability statuses, fare quotes, and verify schema validation.
- [ ] 2.2 Implement `Asia/Kolkata` date and time parsing utilities (`src/safariq/domain/dates.py`) and verify unit tests pass for relative dates, yearless dates, past date rejection, and midnight crossing.
- [ ] 2.3 Implement station normalization and fuzzy candidate matching (`src/safariq/domain/stations.py`) using curated station master and verify disambiguation for "Bokaro" and "Delhi" terminals.
- [ ] 2.4 Implement availability status normalization (`src/safariq/domain/availability.py`) ensuring waitlist/RAC are not converted to confirmed, and verify unit tests pass.
- [ ] 2.5 Implement fare arithmetic using `Decimal` and integer paise (`src/safariq/domain/pricing.py`) without binary floating point, and verify fare rounding unit tests pass.
- [ ] 2.6 Implement hard constraint filtering (`src/safariq/domain/search.py`) for budget, arrival deadline, departure window, and verify filtering unit tests pass.
- [ ] 2.7 Implement deterministic multi-factor JourneyFit scoring (`src/safariq/domain/ranking.py`) and verify ranking unit tests produce deterministic scores and explanations.

## 3. Phase 2 — Database Schema, Repositories & State Persistence

- [ ] 3.1 Define SQLAlchemy async declarative models (`src/safariq/database/models.py`) for `users`, `processed_updates`, `conversations`, `trip_requests`, `search_sessions`, `train_options`, `availability_snapshots`, `fare_quotes`, `ranking_snapshots`, `booking_handoffs`, `monitoring_jobs`, and verify model relationships.
- [ ] 3.2 Implement database engine setup with WAL mode and `busy_timeout` pragmas (`src/safariq/database/engine.py`) and DB initialization script (`scripts/init_db.py`), verifying SQLite tables are created with proper indexes.
- [ ] 3.3 Implement database repositories (`src/safariq/database/repositories/`) for users, update idempotency, trips, quotes, and handoffs, verifying persistence via integration tests.
- [ ] 3.4 Configure LangGraph SQLite checkpointer (`src/safariq/agent/checkpointer.py`) using `aiosqlite` and verify conversation checkpoint save and resume in tests.
- [ ] 3.5 Implement Telegram update deduplication using `processed_updates` repository and verify idempotent update processing in integration test.

## 4. Phase 3 — Mock Provider & Search Vertical Slice

- [ ] 4.1 Create realistic mock railway fixtures (`data/fixtures/trains_bokaro_delhi.json`, `availability.json`, `fares.json`) and seed script (`scripts/seed_demo_data.py`), verifying fixture validity.
- [ ] 4.2 Implement `MockRailwayProvider` (`src/safariq/providers/mock_provider.py`) implementing `RailwayProvider` protocol with explicit `is_demo=True` and verify mock lookup tests pass.
- [ ] 4.3 Implement LangGraph search state machine nodes (`src/safariq/agent/nodes.py`) and routing (`src/safariq/agent/routing.py`) for text search, date validation, station disambiguation, and mock search execution.
- [ ] 4.4 Build end-to-end search pipeline test verifying "Bokaro to Delhi" query yields ranked mock options with visible "DEMO DATA" banner.

## 5. Phase 4 — Pluggable Live Provider Adapter & Integration Gate

- [ ] 5.1 Define `RailwayProvider` protocol and `ProviderCapabilities` flags (`src/safariq/providers/base.py`) and provider registry (`src/safariq/providers/registry.py`), verifying provider selection via environment variables.
- [ ] 5.2 Implement live provider adapter skeleton (`src/safariq/providers/configured_provider.py`) with `httpx` async client, timeouts, bounded retries, rate limiting, and safe error normalization.
- [ ] 5.3 Implement provider response validator rejecting malformed records and attaching retrieval timestamp and provider provenance, verifying validation tests with respx mocks.
- [ ] 5.4 Implement provider verification CLI script (`scripts/check_provider.py`) to test live connectivity or report missing credentials.

## 6. Phase 5 — Gnani Prisma v3 Voice Integration & Fallbacks

- [ ] 6.1 Implement Telegram file download utility (`src/safariq/telegram/file_download.py`) enforcing size limits and temporary file cleanup, verifying audio handling tests.
- [ ] 6.2 Implement Gnani Prisma v3 STT REST client (`src/safariq/speech/gnani_client.py`) with `POST https://api.vachana.ai/stt/v3`, `model=prisma-v3.0`, and `indic-auto` language code.
- [ ] 6.3 Implement voice transcription service (`src/safariq/speech/transcription.py`) integrating Gnani with graceful fallback to text input on 401/403/429/network errors, verifying with mock STT responses.
- [ ] 6.4 Wire voice note processing into LangGraph input classifier node and verify Hindi/Hinglish transcription reaches intent parsing seamlessly.

## 7. Phase 6 — JourneyFit Ranking Engine & What-If Simulator

- [ ] 7.1 Implement evidence-based ranking explanation generator (`src/safariq/domain/ranking.py`) translating verified attributes into natural language reasons, verifying explanation formatting.
- [ ] 7.2 Implement What-If constraint modification logic in LangGraph state (`src/safariq/agent/nodes.py`) allowing users to alter single constraints while retaining existing criteria.
- [ ] 7.3 Implement comparison differentiator highlighting changes between original and simulated results, verifying What-If integration tests.

## 8. Phase 7 — Verified Official Booking Handoff & Drift Detection

- [ ] 8.1 Implement selection refresh service (`src/safariq/services/recommendation_service.py`) re-fetching fresh fare and seat availability upon user train selection.
- [ ] 8.2 Implement price and availability drift detection comparing refreshed quotes with displayed quotes and flagging changes for user confirmation.
- [ ] 8.3 Implement copyable booking summary formatter (`src/safariq/telegram/formatter.py`) including all journey parameters, provider timestamp, and disclaimer that ticket is not yet booked.
- [ ] 8.4 Implement allowlisted IRCTC official portal handoff link generator strictly pointing to `https://www.irctc.co.in/nget` and verify URL validation unit tests.

## 9. Phase 8 — Post-Booking Status Monitoring (P1 Optional)

- [ ] 9.1 Implement SQLite-backed monitoring jobs worker (`src/safariq/scheduler/worker.py` and `jobs.py`) polling due status check jobs.
- [ ] 9.2 Implement train running status check and encrypted PNR check adapters with user opt-in enforcement, verifying scheduler execution tests.
- [ ] 9.3 Implement change deduplication ensuring notifications are emitted only on significant status changes, verifying alert throttling.

## 10. Phase 9 — Telegram Bot Interface, End-to-End Testing & Hardening

- [ ] 10.1 Implement Telegram command handlers (`/start`, `/help`, `/plan`, `/cancel`, `/privacy`) in `src/safariq/telegram/handlers/` and verify command responses.
- [ ] 10.2 Implement inline keyboard generators (`src/safariq/telegram/keyboards.py`) for station selection, sorting profiles, and pagination, keeping `callback_data` payloads under 64 bytes.
- [ ] 10.3 Implement callback query routing (`src/safariq/telegram/handlers/callbacks.py`) with immediate `answerCallbackQuery` calls and graph resumption.
- [ ] 10.4 Implement comprehensive test suite (`tests/e2e/test_trip_search_to_handoff.py`) validating the entire flow: intent -> disambiguation -> search -> ranking -> constraint change -> refresh -> handoff.
- [ ] 10.5 Implement LLM safety tests (`tests/unit/test_llm_safety.py`) asserting that injected hallucinations (fake train numbers, false confirmed seats) are discarded.
- [ ] 10.6 Create `README.md` with complete setup instructions, environment variable documentation, demo mode walk-through, and architectural overview.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result with `openspec validate`.
