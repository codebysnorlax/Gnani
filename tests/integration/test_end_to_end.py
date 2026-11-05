import os
from pathlib import Path
import pytest
from pypdf import PdfReader

from consumerdost.config import settings
from consumerdost.database.engine import AsyncSessionLocal, init_db
from consumerdost.database.repository import DisputeRepository
from consumerdost.documents.pdf_generator import register_fonts
from consumerdost.agent.graph import get_compiled_graph
from consumerdost.agent.state import ConsumerDostState
from consumerdost.agent.nodes import node_bundle, node_tts


@pytest.mark.asyncio
async def test_complete_end_to_end_pipeline():
    """
    Verifies the complete end-to-end flow from raw voice transcript
    to legal assessment, integer calculation, database persistence,
    A4 Unicode PDF generation, NCH dossier, X post, and TTS voice note synthesis.
    """
    # 1. Initialize SQLite Database and Register Fonts
    await init_db()
    register_fonts()

    # 2. Seed brand catalog into SQLite DB
    brands_json = settings.data_dir / "brands.json"
    if brands_json.exists():
        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            await repo.seed_brands(brands_json)

    # 3. Simulate Voice Transcript (with sensitive card/CVV data to verify PII scrubbing)
    raw_transcript = (
        "Maine Flipkart se 14999 ka phone 25 October ko mangaya tha. "
        "Order ID OD987654321012. Screen tooti hui nikli aur inhone refund se mana kar diya. "
        "Mera card number 4111 2222 3333 4444 tha aur CVV 123 tha. "
        "Mera naam Rohan Sharma hai."
    )

    # 4. Initialize State
    initial_state: ConsumerDostState = {
        "telegram_user_id": "test_e2e_user",
        "chat_id": "test_e2e_chat",
        "thread_id": "test_e2e_thread",
        "raw_input_text": raw_transcript,
        "complainant_full_name": "Rohan Sharma",
        "complainant_contact": "rohan@example.com",
        "preferred_language": "hi-IN",
    }

    # 5. Run Intake and Assessment Graph
    graph = await get_compiled_graph()
    assessed_state = await graph.ainvoke(initial_state)

    # Verify PII Scrubbing
    scrubbed = assessed_state.get("sanitized_transcript", "")
    assert "4111" not in scrubbed, "16-digit card must be scrubbed"
    assert "123" not in scrubbed, "CVV must be scrubbed"
    assert "[REDACTED_CARD]" in scrubbed
    assert "OD987654321012" in scrubbed, "Order ID must be preserved"

    # Verify Assessment and Entity Extraction
    assert assessed_state.get("status") == "AWAITING_CONFIRMATION"
    assert assessed_state.get("brand_resolved") is not None
    assert "Flipkart" in assessed_state["brand_resolved"]["corporate_name"]
    assert assessed_state.get("principal_paise") == 1499900
    assert assessed_state.get("total_claim_paise", 0) > 1499900
    assert assessed_state.get("case_reference_id") is not None

    # 6. Generate Tri-Fold Dossier Bundle (PDF, NCH, Social)
    bundle_res = await node_bundle(assessed_state)
    assessed_state.update(bundle_res)

    pdf_path = assessed_state.get("pdf_file_path")
    assert pdf_path is not None and os.path.exists(pdf_path)

    # Inspect PDF contents
    pdf_reader = PdfReader(pdf_path)
    assert len(pdf_reader.pages) >= 1
    pdf_text = "".join(p.extract_text() for p in pdf_reader.pages)
    assert "SECTION 35" in pdf_text.upper()
    assert "FLIPKART" in pdf_text.upper()
    assert "LEGAL DEMAND NOTICE" in pdf_text.upper()

    # Verify NCH Dossier and WhatsApp Link
    nch_text = assessed_state.get("nch_dossier_text", "")
    nch_url = assessed_state.get("nch_whatsapp_url", "")
    assert len(nch_text) > 0 and len(nch_text) < 2000
    assert "wa.me/918860005372" in nch_url

    # Verify Twitter/X Escalation
    twitter_text = assessed_state.get("twitter_draft_text", "")
    twitter_url = assessed_state.get("twitter_intent_url", "")
    assert len(twitter_text) <= 280
    assert "twitter.com/intent/tweet" in twitter_url or "x.com/intent/tweet" in twitter_url

    # 7. Generate TTS Audio Note
    tts_res = await node_tts(assessed_state)
    assessed_state.update(tts_res)

    tts_path = assessed_state.get("tts_audio_path")
    assert tts_path is not None and os.path.exists(tts_path)
    assert os.path.getsize(tts_path) > 0, "Synthesized audio file must not be empty"

    # 8. Persist to SQLite Database & Verify Relational Integrity
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        user = await repo.get_or_create_user(
            telegram_user_id="test_e2e_user",
            telegram_chat_id="test_e2e_chat",
            preferred_language=assessed_state.get("preferred_language", "hi-IN"),
        )
        assert user.telegram_user_id == "test_e2e_user"

        case = await repo.create_dispute_case(
            telegram_user_id="test_e2e_user",
            complainant_name=assessed_state.get("complainant_full_name", "Rohan Sharma"),
            complainant_contact=assessed_state.get("complainant_contact", "rohan@example.com"),
            brand_name=assessed_state["brand_resolved"]["canonical_name"],
            brand_corporate_name=assessed_state["brand_resolved"]["corporate_name"],
            registered_address=assessed_state["brand_resolved"]["registered_address"],
            nodal_email=assessed_state["brand_resolved"]["nodal_email"],
            order_id=assessed_state.get("order_id", "OD987654321012"),
            incident_date=assessed_state.get("incident_date", "2026-10-25"),
            category=assessed_state.get("dispute_category", "E_COMMERCE"),
            issue_type=assessed_state.get("issue_type", "ECOMMERCE_DEFECTIVE_GOODS"),
            principal_paise=assessed_state.get("principal_paise", 1499900),
            interest_paise=assessed_state.get("calculated_interest_paise", 0),
            statutory_penalty_paise=assessed_state.get("statutory_penalty_paise", 0),
            damages_demanded_paise=assessed_state.get("damages_claimed_paise", 0),
            total_demanded_paise=assessed_state.get("total_claim_paise", 1499900),
            narrative_facts_en=assessed_state.get("dispute_narrative_en", "Defective goods delivered."),
            legal_clauses=assessed_state.get("legal_clauses", []),
            status="ASSESSED",
            case_id=assessed_state["case_reference_id"],
        )
        assert case.id == assessed_state["case_reference_id"]
        assert case.principal_paise == 1499900
        assert case.status == "ASSESSED"

        # Save artifacts
        await repo.add_artifact(
            dispute_case_id=case.id,
            artifact_type="LEGAL_NOTICE_PDF",
            file_path=pdf_path,
        )
        await repo.add_artifact(
            dispute_case_id=case.id,
            artifact_type="NCH_DOSSIER",
            content_text=nch_text,
        )

        cases = await repo.get_user_cases("test_e2e_user")
        assert len(cases) >= 1
        found_case = next(c for c in cases if c.id == case.id)
        assert found_case.total_demanded_paise == assessed_state["total_claim_paise"]
