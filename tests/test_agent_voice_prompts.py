import pytest
from pathlib import Path
from saarthi.agent.nodes import node_clarify, node_resolve, node_ingest
from saarthi.agent.state import ConsumerDostState


@pytest.mark.asyncio
async def test_node_clarify_synthesizes_voice_prompt():
    # Conversational priority: order_id before full_name when both are missing
    state: ConsumerDostState = {
        "telegram_user_id": "test_user_123",
        "chat_id": "12345",
        "thread_id": "thread_1",
        "preferred_language": "hi-IN",
        "missing_fields": ["order_id", "full_name"],
    }

    result = await node_clarify(state)
    assert result["status"] == "AWAITING_CLARIFICATION"
    assert "Order ID" in result["clarification_prompt"] or "ऑर्डर ID" in result["clarification_prompt"]
    assert result.get("clarification_target_field") == "order_id"
    assert result["clarification_audio_path"] is not None
    audio_path = Path(result["clarification_audio_path"])
    assert audio_path.exists()
    assert audio_path.name.endswith(".wav")

    # Priority when only full_name is missing
    state_step2: ConsumerDostState = {
        "telegram_user_id": "test_user_123",
        "chat_id": "12345",
        "thread_id": "thread_1",
        "preferred_language": "hi-IN",
        "missing_fields": ["full_name"],
    }
    result2 = await node_clarify(state_step2)
    assert "Full Legal Name" in result2["clarification_prompt"] or "कानूनी नाम" in result2["clarification_prompt"]
    assert result2.get("clarification_target_field") == "full_name"



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


@pytest.mark.asyncio
async def test_messo_brand_resolution_and_conversational_priority():
    from saarthi.domain.brands import resolve_brand
    from saarthi.agent.nodes import node_parse, node_clarify

    # 1. Verify "messo" maps to MEESHO
    brand = resolve_brand("messo")
    assert brand["canonical_name"] == "MEESHO"

    # 2. In node_parse, when user states an issue with messo
    state: ConsumerDostState = {
        "sanitized_transcript": "Hello I have problems with messo",
        "preferred_language": "hi-IN",
    }
    parse_res = await node_parse(state)
    state.update(parse_res)

    # Missing fields must prioritize amount/order_id before full_name
    clarify_res = await node_clarify(state)
    assert clarify_res["status"] == "AWAITING_CLARIFICATION"
    # Target field must be amount or brand, never full_name on first turn
    assert clarify_res["clarification_target_field"] in {"amount", "brand"}
    assert clarify_res["clarification_target_field"] != "full_name"


@pytest.mark.asyncio
async def test_neurons_progress_callback_and_cascade():
    from unittest.mock import patch, MagicMock, AsyncMock
    from saarthi.agent.response_composer import ResponseComposer
    from saarthi.config import settings

    progress_events = []

    async def mock_progress(text: str):
        progress_events.append(text)

    # Simulate OpenRouter failure (e.g. 429 quota exhausted) and Gemini fallback
    mock_or_resp = MagicMock()
    mock_or_resp.status_code = 429

    mock_gemini_resp = MagicMock()
    mock_gemini_resp.text = '{"visible_text": "Maine Meesho se judi aapki samasya note kar li hai. Kripya transaction amount batayein.", "spoken_text": "Kripya transaction amount batayein."}'

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_or_resp), \
         patch("google.genai.Client") as mock_genai_cls, \
         patch.object(settings, "openrouter_api_key", "fake-or-key"), \
         patch.object(settings, "gemini_api_key", "fake-gemini-key"):

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_gemini_resp)
        mock_genai_cls.return_value = mock_client

        res = await ResponseComposer.compose_clarification(
            known_facts={"brand": "MEESHO"},
            target_field="amount",
            language="hi-IN",
            latest_user_text="I have problems with messo",
            voice_character="Shivani",
            progress_callback=mock_progress,
        )

        assert res.engine == "Neurons Mini"
        assert "Connecting to Neurons Nano..." in progress_events
        assert "Could not connect to Neurons Nano. Connecting to Neurons Mini..." in progress_events
        assert "Connected to Neurons Mini\nThinking..." in progress_events



