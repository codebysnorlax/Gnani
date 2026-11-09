import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Chat

from saarthi.agent.graph import get_compiled_graph
from saarthi.agent.state import ConsumerDostState
from saarthi.telegram.bot import confirm_and_advance_slot
from saarthi.agent.regex_fallback import extract_entities_regex


@pytest.mark.asyncio
async def test_offline_fallback_multi_turn_intake():
    """Simulate end-to-end multi-turn intake operating purely in Tier 3 (zero-LLM).
    
    Verifies that without any LLM APIs, the system:
    1. Extracts brand and amount from initial complaint.
    2. Identifies missing fields and asks for Order ID.
    3. Handles 12-digit UTR without Aadhaar redaction and prompts for slot confirmation.
    4. Supports slot edit and updates value on retry.
    5. Correctly parses ordinal date without arbitrary false defaults.
    6. Confirms all slots and transitions to AWAITING_CONFIRMATION with calculated claims.
    """
    # Force Tier 3 deterministic standard engine
    async def mock_extract_dispute_facts(text, progress_callback=None, preferred_model=None):
        draft = extract_entities_regex(text)
        return draft, 3

    mock_bot = AsyncMock()
    mock_msg = MagicMock()
    mock_msg.chat = Chat(id=777, type="private")
    mock_msg.answer = AsyncMock()

    with patch("saarthi.agent.nodes.llm_router.extract_dispute_facts", side_effect=mock_extract_dispute_facts), \
         patch("saarthi.agent.nodes.tts_service.synthesize_speech", new_callable=AsyncMock) as mock_tts, \
         patch("saarthi.telegram.bot.send_voice_with_fallback", new_callable=AsyncMock), \
         patch("saarthi.telegram.bot.save_user_state", new_callable=AsyncMock):

        mock_tts.return_value = "/tmp/mock_voice.wav"
        graph = await get_compiled_graph()

        # Turn 1: Initial user grievance
        state: ConsumerDostState = {
            "telegram_user_id": "user_777",
            "chat_id": "777",
            "thread_id": "thread_777",
            "raw_input_text": "Flipkart se 15000 ka phone mangaya tha broken nikla",
            "preferred_language": "en-IN",
        }
        res1 = await graph.ainvoke(state)
        state.update(res1)

        assert "Flipkart" in (state.get("brand_raw") or "")
        assert state.get("amount_paid_inr") == 15000.0
        assert state.get("incident_date") is None  # Must NOT assign fake default date!
        assert state.get("order_id") is None
        assert state.get("status") == "AWAITING_CLARIFICATION"
        assert state.get("clarification_target_field") == "order_id"

        # Turn 2: User provides 12-digit UTR
        state["raw_input_text"] = "My UTR number is 987654321012"
        res2 = await graph.ainvoke(state)
        state.update(res2)

        assert state.get("pending_confirmation_field") == "order_id"
        assert state.get("pending_confirmation_value") == "987654321012"
        assert "987654321012" in (state.get("clarification_prompt") or "")

        # User confirms UTR slot
        await confirm_and_advance_slot(mock_bot, mock_msg, state, "order_id", "user_777")
        assert state.get("order_id") == "987654321012"
        assert state.get("pending_confirmation_field") is None
        assert state.get("clarification_target_field") == "incident_date"

        # Turn 3a: User provides date "25th October"
        state["raw_input_text"] = "25th October"
        res3a = await graph.ainvoke(state)
        state.update(res3a)

        assert state.get("pending_confirmation_field") == "incident_date"
        assert state.get("pending_confirmation_value") == "2026-10-25"

        # User clicks Edit on date slot
        state["pending_confirmation_field"] = None
        state["pending_confirmation_value"] = None
        state["clarification_target_field"] = "incident_date"

        # Turn 3b: User sends corrected date "26th October"
        state["raw_input_text"] = "26th October"
        res3b = await graph.ainvoke(state)
        state.update(res3b)

        assert state.get("pending_confirmation_field") == "incident_date"
        assert state.get("pending_confirmation_value") == "2026-10-26"

        # User confirms date slot
        await confirm_and_advance_slot(mock_bot, mock_msg, state, "incident_date", "user_777")
        assert state.get("incident_date") == "2026-10-26"
        assert state.get("pending_confirmation_field") is None
        assert state.get("clarification_target_field") == "full_name"

        # Turn 4: User provides full name
        state["raw_input_text"] = "Mera naam Ramesh Kumar hai"
        res4 = await graph.ainvoke(state)
        state.update(res4)

        assert state.get("pending_confirmation_field") == "full_name"
        assert state.get("pending_confirmation_value") == "Ramesh Kumar"

        # User confirms name slot -> transitions to full assessment
        await confirm_and_advance_slot(mock_bot, mock_msg, state, "full_name", "user_777")

        assert state.get("complainant_full_name") == "Ramesh Kumar"
        assert state.get("status") == "AWAITING_CONFIRMATION"
        assert state.get("missing_fields") == []
        assert state.get("brand_resolved") is not None
        assert "Flipkart" in state["brand_resolved"]["corporate_name"]
        assert state.get("total_claim_paise", 0) >= 1500000
        assert state.get("case_reference_id") is not None
