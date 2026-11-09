import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Chat, Message

from saarthi.agent.state import ConsumerDostState
from saarthi.domain.models import DisputeCaseDraft
from saarthi.agent.nodes import node_parse, node_clarify
from saarthi.telegram.keyboards import get_slot_confirmation_keyboard
from saarthi.telegram.bot import confirm_and_advance_slot


@pytest.mark.asyncio
async def test_slot_candidate_extraction_in_node_parse():
    # Mock LLMRouter to simulate Tier 3 fallback extraction
    async def mock_extract(text, progress_callback=None, preferred_model=None):
        from saarthi.agent.regex_fallback import extract_entities_regex
        draft = extract_entities_regex(text)
        return draft, 3

    with patch("saarthi.agent.nodes.llm_router.extract_dispute_facts", side_effect=mock_extract):
        # 1. Date extraction into pending confirmation
        state: ConsumerDostState = {
            "clarification_target_field": "incident_date",
            "raw_input_text": "25th October",
            "missing_fields": ["incident_date"],
        }
        updates = await node_parse(state)
        assert updates.get("pending_confirmation_field") == "incident_date"
        assert updates.get("pending_confirmation_value") == "2026-10-25"

        # 2. Order ID (12-digit UTR) extraction into pending confirmation
        state2: ConsumerDostState = {
            "clarification_target_field": "order_id",
            "raw_input_text": "My UTR number is 987654321012",
            "missing_fields": ["order_id"],
        }
        updates2 = await node_parse(state2)
        assert updates2.get("pending_confirmation_field") == "order_id"
        assert updates2.get("pending_confirmation_value") == "987654321012"

        # 3. Brand extraction into pending confirmation
        state3: ConsumerDostState = {
            "clarification_target_field": "brand",
            "raw_input_text": "Company name is Boat",
            "missing_fields": ["brand"],
        }
        updates3 = await node_parse(state3)
        assert updates3.get("pending_confirmation_field") == "brand"
        assert updates3.get("pending_confirmation_value") == "Boat"


@pytest.mark.asyncio
async def test_slot_confirmation_prompt_and_voice_in_node_clarify():
    # English prompt
    state_en: ConsumerDostState = {
        "preferred_language": "en-IN",
        "pending_confirmation_field": "order_id",
        "pending_confirmation_value": "OD9988776655",
        "missing_fields": ["order_id"],
    }
    with patch("saarthi.agent.nodes.tts_service.synthesize_speech", new_callable=AsyncMock) as mock_tts:
        mock_tts.return_value = "/tmp/mock_confirm.wav"
        res_en = await node_clarify(state_en)

    assert "OD9988776655" in res_en["clarification_prompt"]
    assert "Please confirm if this is correct" in res_en["clarification_prompt"]
    # Verify no greetings in confirmation prompt
    assert "Hello" not in res_en["clarification_prompt"]
    assert "Namaste" not in res_en["clarification_prompt"]
    assert res_en["status"] == "AWAITING_CLARIFICATION"
    assert res_en["pending_confirmation_field"] == "order_id"

    # Hindi prompt
    state_hi: ConsumerDostState = {
        "preferred_language": "hi-IN",
        "pending_confirmation_field": "amount",
        "pending_confirmation_value": 14999.0,
        "missing_fields": ["amount"],
    }
    with patch("saarthi.agent.nodes.tts_service.synthesize_speech", new_callable=AsyncMock) as mock_tts:
        mock_tts.return_value = "/tmp/mock_confirm_hi.wav"
        res_hi = await node_clarify(state_hi)

    assert "₹14,999.00" in res_hi["clarification_prompt"]
    assert "कृपया पुष्टि करें" in res_hi["clarification_prompt"]
    assert "Namaste" not in res_hi["clarification_prompt"]


def test_slot_confirmation_keyboard():
    kb = get_slot_confirmation_keyboard("incident_date")
    buttons = [btn for row in kb.inline_keyboard for btn in row]
    callback_data_list = [btn.callback_data for btn in buttons]

    assert "slot_confirm:incident_date" in callback_data_list
    assert "slot_edit:incident_date" in callback_data_list


@pytest.mark.asyncio
async def test_confirm_slot_transition():
    mock_bot = AsyncMock()
    mock_msg = MagicMock()
    mock_msg.chat = Chat(id=202, type="private")
    mock_msg.answer = AsyncMock()

    state: ConsumerDostState = {
        "telegram_user_id": "test_user_202",
        "chat_id": "202",
        "brand_raw": "Boat",
        "amount_paid_inr": 1999.0,
        "pending_confirmation_field": "order_id",
        "pending_confirmation_value": "OD11223344",
        "missing_fields": ["order_id", "incident_date", "full_name"],
    }

    with patch("saarthi.telegram.bot.save_user_state", new_callable=AsyncMock) as mock_save, \
         patch("saarthi.telegram.bot.send_voice_with_fallback", new_callable=AsyncMock), \
         patch("saarthi.agent.nodes.tts_service.synthesize_speech", new_callable=AsyncMock):
        await confirm_and_advance_slot(mock_bot, mock_msg, state, "order_id", "test_user_202")

    # Value should be committed to canonical state
    assert state.get("order_id") == "OD11223344"
    # Pending slots should be cleared
    assert state.get("pending_confirmation_field") is None
    assert state.get("pending_confirmation_value") is None
    # State saved and next clarification prompt answered
    assert mock_save.called
    assert mock_msg.answer.called
    assert state.get("status") == "AWAITING_CLARIFICATION"
