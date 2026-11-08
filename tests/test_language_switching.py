import pytest
from unittest.mock import AsyncMock, MagicMock
from saarthi.telegram.keyboards import get_language_keyboard, get_welcome_keyboard
from saarthi.telegram.bot import get_or_create_welcome_voice, user_sessions, get_user_state
from saarthi.speech.gnani_tts import SUPPORTED_INDIC_LANGUAGES


def test_language_keyboard_all_10_languages():
    kb = get_language_keyboard()
    callback_data_list = []
    for row in kb.inline_keyboard:
        for button in row:
            callback_data_list.append(button.callback_data)

    assert len(callback_data_list) == 10
    for lang in SUPPORTED_INDIC_LANGUAGES:
        assert f"lang:{lang}" in callback_data_list


def test_welcome_keyboard_has_language_button():
    kb = get_welcome_keyboard()
    button_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "menu:language" in button_callbacks


@pytest.mark.asyncio
async def test_get_or_create_welcome_voice_caching():
    voice_path = await get_or_create_welcome_voice("kn-IN", voice="Shivani")
    assert voice_path is not None
    assert voice_path.exists()
    assert "Shivani" in voice_path.name

    # Second call should retrieve from cache
    cached_path = await get_or_create_welcome_voice("kn-IN", voice="Shivani")
    assert cached_path == voice_path

    # Different voice character must be cached separately
    devansh_path = await get_or_create_welcome_voice("kn-IN", voice="Devansh")
    assert devansh_path is not None
    assert "Devansh" in devansh_path.name
    assert devansh_path != voice_path


def test_user_session_language_update():
    user_id = "test_lang_user"
    chat_id = "1001"
    state = get_user_state(user_id, chat_id)
    assert state["preferred_language"] == "hi-IN"

    # Simulate language update
    state["preferred_language"] = "ta-IN"
    assert get_user_state(user_id, chat_id)["preferred_language"] == "ta-IN"


@pytest.mark.asyncio
async def test_node_ingest_preserves_explicit_language_preference():
    from saarthi.agent.nodes import node_ingest

    # User explicitly selected Hindi
    state = {
        "raw_input_text": "I ordered a phone from Flipkart on 25th October and it arrived damaged.",
        "preferred_language": "hi-IN",
    }
    result = await node_ingest(state)

    # Must preserve hi-IN and not overwrite with en-IN
    assert result["preferred_language"] == "hi-IN"
    assert result["detected_script_language"] == "en-IN"
