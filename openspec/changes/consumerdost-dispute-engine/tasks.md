# Tasks

## 1. Project Setup and Infrastructure

- [ ] 1.1 Configure pyproject.toml dependencies (aiogram, langgraph, reportlab, aiosqlite, sqlalchemy, google-genai, groq, rapidfuzz, pytest-asyncio, respx) and verify installation in virtual environment
- [ ] 1.2 Download and embed Google NotoSans TrueType fonts (NotoSans-Regular.ttf, NotoSans-Bold.ttf) into assets/fonts/ and verify font registration with ReportLab
- [ ] 1.3 Initialize SQLite WAL database schemas (users, disputes, checkpoints) in src/consumerdost/storage/db.py and verify database table creation with unit tests

## 2. Core PII Scrubbing and Brand Resolution

- [ ] 2.1 Implement deterministic regex PII scrubber (scrub_sensitive_pii) covering Aadhaar, PAN, card numbers, CVVs, and banking PINs in src/consumerdost/security/pii.py and verify with unit tests
- [ ] 2.2 Implement brand resolution engine against data/brands.json using RapidFuzz in src/consumerdost/agent/brand_matcher.py with unlisted merchant fallback and verify with unit tests

## 3. 4-Tier Resilient Fact Extraction Pipeline

- [ ] 3.1 Expand extraction schema and multi-tier cascading router in src/consumerdost/agent/extractor.py (Tier 1 Groq/Gemini, Tier 2 OpenRouter, Tier 3 Fixture Cache, Tier 4 Regex fallback) and verify with offline mock tests
- [ ] 3.2 Create golden demo fixture files in data/demo_fixtures/ covering top e-commerce, quick-commerce, and fintech disputes, and verify sub-50ms cache hits

## 4. Deterministic Statutory and Financial Computation Engine

- [ ] 4.1 Implement statutory citation and legal grounds mapper for CPA 2019, E-Commerce Rules 2020, and RBI/DGCA mandates in src/consumerdost/legal/statutory_rules.py and verify mapping test cases
- [ ] 4.2 Implement integer-paise financial mathematics engine in src/consumerdost/legal/financial_math.py calculating 9% equitable interest and tiered compensation and verify accuracy with pytest

## 5. Unicode-Safe Tri-Fold Escalation Document Generation

- [ ] 5.1 Implement ReportLab A4 Legal Demand Notice PDF generator in src/consumerdost/dossier/pdf_generator.py with Rupee symbol rendering, formal legal structure, and Section 35 signature block, verifying output with pypdf
- [ ] 5.2 Implement NCH 1915 WhatsApp deep-link and dossier generator in src/consumerdost/dossier/nch_generator.py and verify text formatting
- [ ] 5.3 Implement X/Twitter escalation post generator in src/consumerdost/dossier/social_generator.py ensuring under-280 character compliance and brand handle inclusion, verifying with tests

## 6. Gnani Speech Integration and Voice Pipeline

- [ ] 6.1 Implement Gnani Prisma v3.0 REST STT client with audio format normalization and 5s timeout in src/consumerdost/speech/gnani_stt.py and verify with mock audio payloads
- [ ] 6.2 Implement Gnani Timbre REST TTS client with 3s timeout and text summary fallback in src/consumerdost/speech/gnani_tts.py and verify with mock response tests

## 7. LangGraph Stateful Workflow and Telegram Bot

- [ ] 7.1 Implement LangGraph conversational state machine with slot-filling, brand validation, and confirmation nodes in src/consumerdost/workflow/graph.py and verify state transitions with unit tests
- [ ] 7.2 Implement aiogram 3.x bot handlers for voice notes, text messages, inline confirmation cards, and /privacy purge commands in src/consumerdost/bot/handlers.py and verify handler behavior
- [ ] 7.3 Create application entrypoint in src/consumerdost/main.py tying together database, bot polling, and graceful shutdown, and verify system startup

## 8. End-to-End System Integration and Verification

- [ ] 8.1 Execute full automated end-to-end simulation from colloquial Hindi voice/text grievance to final PDF, NCH dossier, and X draft, verifying complete output generation

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
