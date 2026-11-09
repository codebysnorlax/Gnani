import pytest
from pathlib import Path

from saarthi.agent.graph import get_compiled_graph, run_atomic_generation
from saarthi.agent.state import ConsumerDostState


@pytest.mark.asyncio
async def test_full_flow_intake_to_atomic_generation():
    """Verify end-to-end LangGraph state machine from text/intake to atomic GENERATED state."""
    intake_graph = await get_compiled_graph()
    import uuid
    uid = uuid.uuid4().hex[:8]
    state: ConsumerDostState = {
        "telegram_user_id": f"atomic_user_{uid}",
        "chat_id": f"atomic_chat_{uid}",
        "thread_id": f"thread_atomic_{uid}",
        "preferred_language": "hi-IN",
        "raw_input_text": (
            "Maine Flipkart se 14999 ka phone 25 October ko mangaya tha. "
            "Order ID OD3091823901. Box khola toh screen tooti hui thi. "
            "Mera naam Rohan Sharma hai aur email rohan@example.com."
        ),
        "demo_type": "flipkart",
        "is_demo": True,
    }

    # 1. Run intake & dispute assessment
    intake_result = await intake_graph.ainvoke(state)
    assert intake_result["status"] == "AWAITING_CONFIRMATION"
    assert intake_result.get("total_claim_paise", 0) > 1499900
    assert intake_result.get("brand_resolved") is not None
    assert intake_result.get("case_reference_id") is not None

    state.update(intake_result)

    # 2. Run atomic generation pipeline (bundle -> tts)
    gen_result = await run_atomic_generation(state)
    state.update(gen_result)

    # 3. Verify atomic state completeness
    assert state.get("status") == "GENERATED"
    assert state.get("pdf_file_path") is not None
    assert Path(state["pdf_file_path"]).exists()
    assert state.get("nch_dossier_text") is not None
    assert "NCH 1915" in state["nch_dossier_text"]
    assert state.get("twitter_draft_text") is not None
    assert len(state["twitter_draft_text"]) <= 280
    assert state.get("tts_audio_path") is not None
    assert Path(state["tts_audio_path"]).exists()


@pytest.mark.asyncio
async def test_atomic_bundle_idempotency_no_duplicates():
    """Verify that multiple runs with the same case_reference_id reuse artifacts and do not duplicate DB records."""
    from saarthi.database.repository import DisputeRepository
    from saarthi.database.engine import AsyncSessionLocal, init_db

    await init_db()

    case_ref = "SRTH-2026-IDEM01"
    state: ConsumerDostState = {
        "telegram_user_id": "test_idem_user",
        "chat_id": "idem_chat_1",
        "thread_id": "idem_thread_1",
        "preferred_language": "en-IN",
        "case_reference_id": case_ref,
        "complainant_full_name": "Priya Nair",
        "complainant_contact": "priya@example.com",
        "amount_paid_inr": 25000.0,
        "incident_date": "2026-10-15",
        "order_id": "OD9988776655",
        "issue_type": "ECOMMERCE_DEFECTIVE_GOODS",
        "dispute_category": "E_COMMERCE",
        "dispute_narrative_en": "Defective electronics delivered and return rejected.",
        "brand_resolved": {
            "corporate_name": "Flipkart Internet Private Limited",
            "registered_address": "Bengaluru, Karnataka",
            "nodal_email": "nodal@flipkart.com",
            "twitter_handle": "@FlipkartSupport",
        },
    }

    # Run 1: generate bundle
    res1 = await run_atomic_generation(state)
    assert res1["status"] == "GENERATED"
    pdf1 = res1["pdf_file_path"]
    assert pdf1 is not None and Path(pdf1).exists()

    # Save to DB (simulating bot handler)
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        await repo.create_dispute_case(
            case_id=case_ref,
            telegram_user_id="test_idem_user",
            complainant_name="Priya Nair",
            complainant_contact="priya@example.com",
            brand_name="Flipkart",
            brand_corporate_name="Flipkart Internet Private Limited",
            registered_address="Bengaluru",
            nodal_email="nodal@flipkart.com",
            order_id="OD9988776655",
            incident_date="2026-10-15",
            category="E_COMMERCE",
            issue_type="ECOMMERCE_DEFECTIVE_GOODS",
            principal_paise=2500000,
            interest_paise=0,
            statutory_penalty_paise=0,
            damages_demanded_paise=0,
            total_demanded_paise=2500000,
            narrative_facts_en="Defective goods",
            legal_clauses=["Section 2(9) CPA 2019"],
            status="BUNDLE_GENERATED",
        )
        await repo.add_artifact(case_ref, "LEGAL_NOTICE_PDF", file_path=pdf1)
        await repo.add_artifact(case_ref, "NCH_DOSSIER", content_text=res1["nch_dossier_text"])

    # Run 2: generate bundle again with same state and case_ref
    state.update(res1)
    res2 = await run_atomic_generation(state)
    assert res2["status"] == "GENERATED"
    assert res2["pdf_file_path"] == pdf1

    # Save to DB again (simulating repeated Telegram callback / retry)
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        await repo.create_dispute_case(
            case_id=case_ref,
            telegram_user_id="test_idem_user",
            complainant_name="Priya Nair",
            complainant_contact="priya@example.com",
            brand_name="Flipkart",
            brand_corporate_name="Flipkart Internet Private Limited",
            registered_address="Bengaluru",
            nodal_email="nodal@flipkart.com",
            order_id="OD9988776655",
            incident_date="2026-10-15",
            category="E_COMMERCE",
            issue_type="ECOMMERCE_DEFECTIVE_GOODS",
            principal_paise=2500000,
            interest_paise=0,
            statutory_penalty_paise=0,
            damages_demanded_paise=0,
            total_demanded_paise=2500000,
            narrative_facts_en="Defective goods",
            legal_clauses=["Section 2(9) CPA 2019"],
            status="BUNDLE_GENERATED",
        )
        await repo.add_artifact(case_ref, "LEGAL_NOTICE_PDF", file_path=pdf1)
        await repo.add_artifact(case_ref, "NCH_DOSSIER", content_text=res2["nch_dossier_text"])

        # Check DB row counts
        case = await repo.get_case_by_id(case_ref)
        assert case is not None
        artifacts = await repo.get_artifacts_by_case(case_ref)
        # Should only have 2 artifacts (PDF and NCH), not duplicated to 4
        assert len(artifacts) == 2


@pytest.mark.asyncio
async def test_atomic_bundle_partial_failure_reporting():
    """Verify that when one artifact fails (e.g. PDF generation exception), other artifacts still generate and status is PARTIALLY_GENERATED."""
    from unittest.mock import patch

    case_ref = "SRTH-2026-PARTIAL01"
    state: ConsumerDostState = {
        "telegram_user_id": "test_partial_user",
        "chat_id": "partial_chat_1",
        "thread_id": "partial_thread_1",
        "preferred_language": "hi-IN",
        "case_reference_id": case_ref,
        "complainant_full_name": "Amit Verma",
        "complainant_contact": "amit@example.com",
        "amount_paid_inr": 12000.0,
        "incident_date": "2026-10-10",
        "order_id": "OD1122334455",
        "issue_type": "ECOMMERCE_REFUND_DELAY_OR_DENIAL",
        "dispute_category": "E_COMMERCE",
        "dispute_narrative_en": "Refund delayed beyond statutory 14-day limit.",
        "brand_resolved": {
            "corporate_name": "Flipkart Internet Private Limited",
            "registered_address": "Bengaluru, Karnataka",
            "nodal_email": "nodal@flipkart.com",
            "twitter_handle": "@FlipkartSupport",
        },
    }

    def mock_fail_pdf(*args, **kwargs):
        raise IOError("Simulated disk error during PDF rendering")

    with patch("saarthi.agent.nodes.generate_legal_notice_pdf", side_effect=mock_fail_pdf):
        res = await run_atomic_generation(state)

    assert res["status"] == "PARTIALLY_GENERATED"
    assert "PDF_LEGAL_NOTICE" in res["bundle_errors"]
    assert res.get("pdf_file_path") is None
    # Verify other artifacts still generated
    assert res.get("nch_dossier_text") is not None
    assert "NCH 1915" in res["nch_dossier_text"]
    assert res.get("twitter_draft_text") is not None

