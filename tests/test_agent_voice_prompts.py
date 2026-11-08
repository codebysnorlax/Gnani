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
    assert "Full Legal Name" in result["clarification_prompt"] or "कानूनी नाम" in result["clarification_prompt"]
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
    assert "Order ID" in result2["clarification_prompt"] or "ऑर्डर ID" in result2["clarification_prompt"]
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


@pytest.mark.asyncio
async def test_node_clarify_respects_voice_character():
    from unittest.mock import patch
    from saarthi.speech.gnani_tts import tts_service

    state: ConsumerDostState = {
        "telegram_user_id": "test_user_789",
        "chat_id": "12345",
        "thread_id": "thread_voice",
        "preferred_language": "hi-IN",
        "preferred_voice_character": "Chetana",
        "missing_fields": ["order_id"],
    }

    with patch.object(tts_service, "synthesize_speech", wraps=tts_service.synthesize_speech) as mock_synth:
        result = await node_clarify(state)
        assert result["status"] == "AWAITING_CLARIFICATION"
        assert mock_synth.called
        kwargs = mock_synth.call_args[1]
        assert kwargs.get("voice") == "Chetana"


@pytest.mark.asyncio
async def test_compose_clarification_openrouter_cascade():
    from unittest.mock import patch, MagicMock, AsyncMock
    from saarthi.agent.response_composer import ResponseComposer
    from saarthi.config import settings

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"visible_text": "I noticed your issue with Flipkart. Please provide your Order ID.", "spoken_text": "Please share your Order ID."}'
                }
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp), patch.object(settings, "openrouter_api_key", "mock-or-key"):
        res = await ResponseComposer.compose_clarification(
            known_facts={"brand": "Flipkart", "amount": 15000},
            target_field="order_id",
            language="en-IN",
            latest_user_text="I bought a phone on Flipkart",
            voice_character="Shivani",
        )
        assert "Flipkart" in res.visible_text
        assert "Order ID" in res.visible_text
        assert res.spoken_text == "Please share your Order ID."


@pytest.mark.asyncio
async def test_compose_clarification_fallback_to_template():
    from unittest.mock import patch
    from saarthi.agent.response_composer import ResponseComposer
    from saarthi.config import settings

    with patch.object(settings, "openrouter_api_key", ""), patch.object(settings, "gemini_api_key", ""):
        res = await ResponseComposer.compose_clarification(
            known_facts={"brand": "Amazon", "amount": 25000},
            target_field="full_name",
            language="en-IN",
            latest_user_text="Amazon order issue",
            voice_character="Shivani",
        )
        assert "Amazon" in res.visible_text
        assert "Full Legal Name" in res.visible_text
        assert res.target_field == "full_name"


@pytest.mark.asyncio
async def test_node_parse_contextual_short_answers():
    from saarthi.agent.nodes import node_parse

    # 1. Short answer for legal name
    state_name: ConsumerDostState = {
        "sanitized_transcript": "Ravi Ranjan Sharma",
        "clarification_target_field": "full_name",
        "brand_raw": "Flipkart",
        "amount_paid_inr": 15000.0,
    }
    res_name = await node_parse(state_name)
    assert res_name.get("complainant_full_name") == "Ravi Ranjan Sharma"

    # 2. Short answer for amount
    state_amt: ConsumerDostState = {
        "sanitized_transcript": "30000",
        "clarification_target_field": "amount",
        "brand_raw": "Amazon",
    }
    res_amt = await node_parse(state_amt)
    assert res_amt.get("amount_paid_inr") == 30000.0

    # 3. Short answer for order id
    state_order: ConsumerDostState = {
        "sanitized_transcript": "Id: 8261829",
        "clarification_target_field": "order_id",
        "brand_raw": "Flipkart",
    }
    res_order = await node_parse(state_order)
    assert res_order.get("order_id") == "8261829"

    # 4. Short answer for incident date
    state_date: ConsumerDostState = {
        "sanitized_transcript": "25 Oct 2026",
        "clarification_target_field": "incident_date",
        "brand_raw": "Flipkart",
    }
    res_date = await node_parse(state_date)
    assert res_date.get("incident_date") in {"2026-10-25", "25 Oct 2026"}


