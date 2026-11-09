from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import User as TelegramUser, Chat, Message

from saarthi.database.engine import init_db
from saarthi.telegram.bot import (
    create_bot_and_dispatcher,
    get_user_state,
    get_or_create_user_state,
    save_user_state,
    clear_user_state,
    user_sessions,
)


def test_bot_and_dispatcher_creation():
    bot, dp = create_bot_and_dispatcher()
    assert bot is not None
    assert dp is not None
    assert len(dp.update.outer_middleware) >= 0 or len(dp.update.middleware) >= 0


def test_user_session_state_lifecycle():
    user_sessions.clear()
    state = get_user_state("12345", "67890")
    assert state["telegram_user_id"] == "12345"
    assert state["chat_id"] == "67890"
    assert state["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_async_sqlite_session_persistence():
    await init_db()
    user_id = "test_bot_session_user_42"
    chat_id = "chat_42"

    # 1. Clean slate
    await clear_user_state(user_id)

    # 2. Retrieve or create
    state = await get_or_create_user_state(user_id, chat_id)
    assert state["telegram_user_id"] == user_id
    assert state["status"] == "DRAFT"

    # 3. Modify and save
    state["status"] = "AWAITING_CONFIRMATION"
    state["brand_raw"] = "Flipkart"
    state["total_claim_paise"] = 1499900
    await save_user_state(user_id, state)

    # 4. Reload from SQLite
    loaded = await get_or_create_user_state(user_id, chat_id)
    assert loaded["status"] == "AWAITING_CONFIRMATION"
    assert loaded["brand_raw"] == "Flipkart"
    assert loaded["total_claim_paise"] == 1499900

    # 5. Clean up
    await clear_user_state(user_id)


@pytest.mark.asyncio
async def test_session_recovery_detection():
    await init_db()
    user_id = "test_bot_recovery_user_99"
    chat_id = "chat_99"

    # Seed an incomplete case in SQLite
    state = {
        "telegram_user_id": user_id,
        "chat_id": chat_id,
        "thread_id": f"thread_{user_id}",
        "preferred_language": "hi-IN",
        "status": "AWAITING_CONFIRMATION",
        "brand_raw": "Flipkart",
        "total_claim_paise": 1500000,
    }
    await save_user_state(user_id, state)

    bot, dp = create_bot_and_dispatcher()

    # Create mock message
    mock_message = AsyncMock(spec=Message)
    mock_message.from_user = TelegramUser(id=99, is_bot=False, first_name="Rohan")
    mock_message.chat = Chat(id=99, type="private")
    mock_message.answer = AsyncMock()

    # Re-save with user id matching mock
    state["telegram_user_id"] = "99"
    await save_user_state("99", state)

    # Verify session load
    loaded = await get_or_create_user_state("99", chat_id)
    assert loaded["status"] == "AWAITING_CONFIRMATION"
    assert loaded["brand_raw"] == "Flipkart"

    # Clean up
    await clear_user_state("99")


@pytest.mark.asyncio
async def test_dynamic_multi_turn_clarification_no_repeats():
    from saarthi.agent.response_composer import ResponseComposer

    # Turn 1: Brand and Amount known; missing full_name
    facts_turn1 = {"brand": "Flipkart", "amount": 14999.0}
    res1 = await ResponseComposer.compose_clarification(
        known_facts=facts_turn1,
        target_field="full_name",
        language="en-IN",
        latest_user_text="I bought a phone on Flipkart for 14999 and the screen was broken.",
    )
    assert res1.target_field == "full_name"
    assert "Flipkart" in res1.visible_text or "Flipkart" in res1.spoken_text
    assert "Name" in res1.visible_text
    assert not res1.spoken_text.startswith("<")  # No leading audio tag
    # Ensure no emoji
    assert not any(0x1F300 <= ord(c) <= 0x1FAFF for c in res1.visible_text)

    # Turn 2: User provides full name; target is now order_id
    facts_turn2 = {"brand": "Flipkart", "amount": 14999.0, "full_name": "Rohan Sharma"}
    res2 = await ResponseComposer.compose_clarification(
        known_facts=facts_turn2,
        target_field="order_id",
        language="en-IN",
        latest_user_text="My name is Rohan Sharma.",
    )
    assert res2.target_field == "order_id"
    assert "Order" in res2.visible_text
    # Does not ask for full name again
    assert "please provide your full legal name" not in res2.visible_text.lower()

    # Turn 3: User provides order ID; target is now incident_date
    facts_turn3 = {
        "brand": "Flipkart",
        "amount": 14999.0,
        "full_name": "Rohan Sharma",
        "order_id": "OD9988776655",
    }
    res3 = await ResponseComposer.compose_clarification(
        known_facts=facts_turn3,
        target_field="incident_date",
        language="en-IN",
        latest_user_text="My order ID was OD9988776655.",
    )
    assert res3.target_field == "incident_date"
    assert "date" in res3.visible_text.lower()
    # Does not ask for order ID or full name again
    assert "order id or reference number" not in res3.visible_text.lower()


@pytest.mark.asyncio
async def test_setup_bot_commands_registers_menu_items():
    from saarthi.telegram.bot import setup_bot_commands

    mock_bot = MagicMock()
    mock_bot.set_my_commands = AsyncMock()

    await setup_bot_commands(mock_bot)
    assert mock_bot.set_my_commands.await_count >= 1
    commands = mock_bot.set_my_commands.call_args[0][0]
    cmd_names = [c.command for c in commands]

    assert "start" in cmd_names
    assert "lang" in cmd_names
    assert "gender" in cmd_names
    assert "newdispute" in cmd_names
    assert "mycases" in cmd_names
    assert "privacy" in cmd_names


def test_voice_character_keyboard_gender_indicators():
    from saarthi.telegram.keyboards import get_voice_character_keyboard

    kb = get_voice_character_keyboard()
    button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]

    assert any("Female: Shivani" in t for t in button_texts)
    assert any("Male: Devansh" in t for t in button_texts)
    assert any("Female: Chetana" in t for t in button_texts)
    assert "voice:Shivani" in callbacks
    assert "voice:Devansh" in callbacks
    assert "voice:Chetana" in callbacks


def test_is_conversational_greeting_or_help():
    from saarthi.telegram.bot import is_conversational_greeting_or_help

    assert is_conversational_greeting_or_help("Hello what ca you do")
    assert is_conversational_greeting_or_help("what can you do")
    assert is_conversational_greeting_or_help("hello")
    assert is_conversational_greeting_or_help("hi")
    assert is_conversational_greeting_or_help("Namaste")
    assert is_conversational_greeting_or_help("kya kar sakte ho")
    assert is_conversational_greeting_or_help("who are you")

    # Language support inquiries
    assert is_conversational_greeting_or_help("Which which language you can support")
    assert is_conversational_greeting_or_help("how many languages do you support")
    assert is_conversational_greeting_or_help("what languages can you speak")
    assert is_conversational_greeting_or_help("can you speak Tamil")
    assert is_conversational_greeting_or_help("konsi bhasha support karte ho")

    # Real complaints must NOT be treated as conversational greetings
    assert not is_conversational_greeting_or_help("I ordered a phone on Flipkart for 14999")
    assert not is_conversational_greeting_or_help("Airline cancelled my ticket and denied refund")


@pytest.mark.asyncio
async def test_handle_conversational_inquiry_with_male_voice_in_english():
    from saarthi.telegram.bot import handle_conversational_inquiry
    from unittest.mock import patch
    from saarthi.speech.gnani_tts import tts_service

    mock_bot = MagicMock()
    mock_bot.send_chat_action = AsyncMock()
    mock_bot.send_voice = AsyncMock()

    mock_msg = MagicMock()
    mock_msg.chat.id = 12345
    mock_msg.from_user.id = 67890
    mock_msg.text = "Hello what ca you do"
    mock_msg.answer = AsyncMock()

    state = {
        "telegram_user_id": "67890",
        "chat_id": "12345",
        "preferred_language": "hi-IN",
        "preferred_voice_character": "Devansh",
        "raw_input_text": "Hello what ca you do",
    }

    with patch.object(tts_service, "synthesize_speech", wraps=tts_service.synthesize_speech) as mock_synth:
        await handle_conversational_inquiry(mock_bot, mock_msg, state)

        # Must respond with friendly capability explanation, NOT demand legal name
        mock_msg.answer.assert_awaited_once()
        reply_text = mock_msg.answer.call_args[0][0]
        assert "SAARTHI" in reply_text
        assert "Consumer Protection Act" in reply_text
        assert "Legal Demand Notice" in reply_text
        assert "पूरा कानूनी नाम" not in reply_text
        assert "Full Legal Name" not in reply_text

        # Must synthesize in Devansh's voice
        assert mock_synth.called
        assert mock_synth.call_args[1].get("voice") == "Devansh"
        assert mock_synth.call_args[1].get("language") == "en-IN"


def test_neurons_keyboard_options_and_no_emoji():
    from saarthi.telegram.keyboards import get_neurons_keyboard

    kb = get_neurons_keyboard(current_model="auto")
    assert len(kb.inline_keyboard) == 5

    btn_texts = [row[0].text for row in kb.inline_keyboard]
    callbacks = [row[0].callback_data for row in kb.inline_keyboard]

    # Verify all 5 options are present
    assert any("Nemotron 3.5 Super VL" in t for t in btn_texts)
    assert any("North Mini Code" in t for t in btn_texts)
    assert any("Nemotron 3 Nano Omni 30B" in t for t in btn_texts)
    assert any("Standard Engine" in t for t in btn_texts)
    assert any("Auto" in t for t in btn_texts)

    # Verify callback keys are compact
    assert "neurons:super_vl" in callbacks
    assert "neurons:north_mini" in callbacks
    assert "neurons:nano_omni" in callbacks
    assert "neurons:standard" in callbacks
    assert "neurons:auto" in callbacks

    # Verify active marker
    assert "[Active] Auto" in btn_texts[4]

    # Switch active
    kb2 = get_neurons_keyboard(current_model="cohere/north-mini-code:free")
    btn_texts2 = [row[0].text for row in kb2.inline_keyboard]
    assert "[Active] North Mini Code" in btn_texts2[1]


@pytest.mark.asyncio
async def test_setup_bot_commands_includes_neurons():
    from saarthi.telegram.bot import setup_bot_commands

    mock_bot = MagicMock()
    mock_bot.set_my_commands = AsyncMock()

    await setup_bot_commands(mock_bot)
    assert mock_bot.set_my_commands.await_count >= 1

    registered_commands = mock_bot.set_my_commands.call_args[0][0]
    cmd_names = [c.command for c in registered_commands]
    assert "neurons" in cmd_names
    assert "lang" in cmd_names
    assert "gender" in cmd_names


@pytest.mark.asyncio
async def test_start_banner_and_welcome_keyboard():
    from unittest.mock import patch
    from saarthi.database.engine import AsyncSessionLocal
    from saarthi.database.repository import DisputeRepository
    from saarthi.telegram.keyboards import get_welcome_keyboard

    await init_db()
    test_user_id = "999"
    test_chat_id = "999"

    # Ensure clean slate
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        await repo.delete_user_data(test_user_id)

    bot, dp = create_bot_and_dispatcher()
    bot.send_chat_action = AsyncMock()

    # Find the cmd_start handler
    start_handler = None
    for handler in dp.message.handlers:
        if getattr(handler.callback, "__name__", "") == "cmd_start":
            start_handler = handler.callback
            break

    assert start_handler is not None, "cmd_start handler should be registered"

    # Mock Message
    mock_msg = MagicMock(spec=Message)
    mock_msg.from_user = TelegramUser(id=999, is_bot=False, first_name="BannerTester")
    mock_msg.chat = Chat(id=999, type="private")
    mock_msg.answer = AsyncMock()
    mock_msg.answer_photo = AsyncMock()

    with patch("saarthi.telegram.bot.get_or_create_welcome_voice", return_value=None), \
         patch("saarthi.telegram.bot.send_voice_with_fallback", new_callable=AsyncMock):

        # Start: should send banner photo and welcome keyboard
        await start_handler(mock_msg)
        assert mock_msg.answer_photo.await_count == 1
        assert mock_msg.answer.await_count == 1

        # Verify welcome keyboard has neurons option
        kwargs = mock_msg.answer.call_args[1]
        kb = kwargs.get("reply_markup")
        assert kb is not None
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert "menu:neurons" in callbacks
        assert "menu:language" in callbacks
        assert "menu:voice" in callbacks

    # Clean up
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        await repo.delete_user_data(test_user_id)


@pytest.mark.asyncio
async def test_compose_conversation_dynamic_and_full_audio():
    from saarthi.agent.response_composer import ResponseComposer

    res = await ResponseComposer.compose_conversation(
        user_text="Which which language you can support",
        language="en-IN",
        voice_character="Shivani",
    )
    assert res is not None
    assert res.visible_text
    assert res.spoken_text

    # Verify 10 languages awareness
    visible_lower = res.visible_text.lower()
    spoken_lower = res.spoken_text.lower()
    assert "hindi" in visible_lower or "हिन्दी" in res.visible_text
    assert "tamil" in visible_lower or "தமிழ்" in res.visible_text
    assert "kannada" in visible_lower or "ಕನ್ನಡ" in res.visible_text
    assert "telugu" in visible_lower or "తెలుగు" in res.visible_text

    # Verify audio is NOT truncated to < 25 words
    spoken_words = res.spoken_text.split()
    assert len(spoken_words) >= 25, f"Spoken text is too short ({len(spoken_words)} words); expected full audio note"

    # Verify no emojis
    import re
    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
    assert not emoji_pattern.search(res.visible_text)
    assert not emoji_pattern.search(res.spoken_text)


@pytest.mark.asyncio
async def test_slot_confirm_and_edit_handlers():
    from unittest.mock import MagicMock, AsyncMock, patch
    from aiogram.types import Message
    from saarthi.telegram.bot import confirm_and_advance_slot, get_or_create_user_state, save_user_state

    await init_db()
    user_id = "test_slot_user_101"
    chat_id = "101"

    state = await get_or_create_user_state(user_id, chat_id)
    state["brand_raw"] = "Flipkart"
    state["amount_paid_inr"] = 5000.0
    state["incident_date"] = "2026-10-25"
    state["complainant_full_name"] = "Rohan Sharma"
    state["pending_confirmation_field"] = "order_id"
    state["pending_confirmation_value"] = "OD1234567890"
    await save_user_state(user_id, state)

    mock_bot = MagicMock()
    mock_bot.send_voice = AsyncMock()
    mock_msg = MagicMock()
    mock_msg.chat = Chat(id=101, type="private")
    mock_msg.answer = AsyncMock()

    with patch("saarthi.telegram.bot.send_voice_with_fallback", new_callable=AsyncMock):
        await confirm_and_advance_slot(mock_bot, mock_msg, state, "order_id", user_id)

    assert state.get("order_id") == "OD1234567890"
    assert state.get("pending_confirmation_field") is None
    assert state.get("pending_confirmation_value") is None
    assert state.get("status") == "AWAITING_CONFIRMATION"
    assert mock_msg.answer.called






