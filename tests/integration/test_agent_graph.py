import pytest
from saarthi.agent.graph import get_compiled_graph
from saarthi.agent.state import ConsumerDostState


@pytest.mark.asyncio
async def test_agent_graph_missing_field_clarification():
    graph = await get_compiled_graph()
    initial_state: ConsumerDostState = {
        "telegram_user_id": "test_123",
        "chat_id": "chat_123",
        "thread_id": "thread_123",
        "raw_input_text": "Maine phone mangaya tha par screen tooti thi.",
        "preferred_language": "hi-IN",
    }

    # Execute workflow from start
    result = await graph.ainvoke(initial_state)

    # Missing brand, order ID, amount, name
    assert result.get("status") == "AWAITING_CLARIFICATION"
    assert result.get("clarification_prompt") is not None
    assert len(result.get("missing_fields", [])) > 0
    assert result.get("pdf_file_path") is None
    assert result.get("nch_dossier_text") is None
    assert result.get("twitter_draft_text") is None


@pytest.mark.asyncio
async def test_agent_graph_incomplete_case_rejects_bundle():
    from saarthi.agent.nodes import node_bundle
    incomplete_state: ConsumerDostState = {
        "status": "AWAITING_CLARIFICATION",
        "missing_fields": ["order_id", "full_name"],
        "amount_paid_inr": 14999.0,
    }
    with pytest.raises(ValueError, match="Cannot generate document bundle"):
        await node_bundle(incomplete_state)



@pytest.mark.asyncio
async def test_agent_graph_full_resolution():
    graph = await get_compiled_graph()
    initial_state: ConsumerDostState = {
        "telegram_user_id": "test_123",
        "chat_id": "chat_123",
        "thread_id": "thread_123",
        "raw_input_text": (
            "Maine Flipkart se 14999 ka phone 25 October ko mangaya tha. "
            "Order ID OD3091823901. Screen tooti hui nikli. "
            "Mera naam Rohan Sharma hai."
        ),
        "complainant_full_name": "Rohan Sharma",
        "complainant_contact": "rohan@example.com",
        "preferred_language": "hi-IN",
    }

    # Run intake through resolution
    result = await graph.ainvoke(initial_state)

    assert result.get("status") == "AWAITING_CONFIRMATION"
    assert result.get("brand_resolved") is not None
    assert "Flipkart" in result["brand_resolved"]["corporate_name"]
    assert result.get("total_claim_paise", 0) > 1499900
    assert result.get("case_reference_id") is not None


@pytest.mark.asyncio
async def test_agent_graph_bundle_and_tts():
    # Test bundle execution node
    from saarthi.agent.nodes import node_bundle, node_tts
    state: ConsumerDostState = {
        "case_reference_id": "CD-2026-TEST",
        "amount_paid_inr": 14999.00,
        "incident_date": "2026-10-25",
        "complainant_full_name": "Rohan Sharma",
        "complainant_contact": "rohan@example.com",
        "issue_type": "ECOMMERCE_DEFECTIVE_GOODS",
        "dispute_category": "E_COMMERCE",
        "dispute_narrative_en": "Delivered phone with broken screen; return denied.",
        "preferred_language": "hi-IN",
    }

    bundle_res = await node_bundle(state)
    state.update(bundle_res)

    assert state.get("pdf_file_path") is not None
    assert "Legal_Notice_CD-2026-TEST.pdf" in state["pdf_file_path"]
    assert state.get("nch_dossier_text") is not None
    assert state.get("twitter_draft_text") is not None

    tts_res = await node_tts(state)
    assert tts_res.get("tts_audio_path") is not None
