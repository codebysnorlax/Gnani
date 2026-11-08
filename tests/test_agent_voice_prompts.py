import pytest
from pathlib import Path
from saarthi.agent.nodes import node_clarify, node_resolve, node_ingest
from saarthi.agent.state import ConsumerDostState


@pytest.mark.asyncio
async def test_node_clarify_synthesizes_voice_prompt():
    # Priority 1: full_name when multiple are missing
    state: ConsumerDostState = {
        "telegram_user_id": "test_user_123",
        "chat_id": "12345",
        "thread_id": "thread_1",
        "preferred_language": "hi-IN",
        "missing_fields": ["order_id", "full_name"],
    }

    result = await node_clarify(state)
    assert result["status"] == "AWAITING_CLARIFICATION"
    assert result["clarification_prompt"] is not None
    assert "Full Legal Name" in result["clarification_prompt"]
    assert result.get("clarification_target_field") == "full_name"
    assert result["clarification_audio_path"] is not None
    audio_path = Path(result["clarification_audio_path"])
    assert audio_path.exists()
    assert audio_path.name.endswith(".wav")

    # Priority 2: order_id when full_name is resolved
    state_step2: ConsumerDostState = {
        "telegram_user_id": "test_user_123",
        "chat_id": "12345",
        "thread_id": "thread_1",
        "preferred_language": "hi-IN",
        "missing_fields": ["order_id"],
    }
    result2 = await node_clarify(state_step2)
    assert "Order ID" in result2["clarification_prompt"]
    assert result2.get("clarification_target_field") == "order_id"



@pytest.mark.asyncio
async def test_node_resolve_synthesizes_assessment_audio():
    state: ConsumerDostState = {
        "telegram_user_id": "test_user_456",
        "chat_id": "67890",
        "thread_id": "thread_2",
        "preferred_language": "en-IN",
        "brand_raw": "Flipkart",
        "amount_paid_inr": 15000.0,
        "incident_date": "2026-10-25",
        "order_id": "OD99999999",
        "complainant_full_name": "Rohan Sharma",
        "issue_type": "ECOMMERCE_REFUND_DELAY_OR_DENIAL",
    }

    result = await node_resolve(state)
    assert result["status"] == "AWAITING_CONFIRMATION"
    assert result["total_claim_paise"] > 1500000
    assert result["assessment_audio_path"] is not None
    audio_path = Path(result["assessment_audio_path"])
    assert audio_path.exists()
    assert audio_path.name.endswith(".wav")


@pytest.mark.asyncio
async def test_node_ingest_auto_detects_kannada():
    state: ConsumerDostState = {
        "raw_input_text": "ನನ್ನ ಫ್ಲಿಪ್‌ಕಾರ್ಟ್ ಆರ್ಡರ್ ತಲುಪಿಲ್ಲ",
        "preferred_language": "hi-IN",
    }
    result = await node_ingest(state)
    assert result["preferred_language"] == "hi-IN"
    assert result["detected_script_language"] == "kn-IN"
