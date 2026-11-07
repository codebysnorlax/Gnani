import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.enums import ChatAction
from aiogram.types import Message, Chat, User

from consumerdost.telegram.bot import (
    send_voice_with_fallback,
    process_workflow_turn,
)
from consumerdost.agent.state import ConsumerDostState


@pytest.mark.asyncio
async def test_send_voice_with_fallback_success(tmp_path: Path):
    audio_file = tmp_path / "voice_sample.wav"
    audio_file.write_bytes(b"RIFF sample audio")

    mock_bot = AsyncMock()
    result = await send_voice_with_fallback(
        bot=mock_bot,
        chat_id=12345,
        audio_path=audio_file,
        caption="Sample Voice Note",
    )

    assert result is True
    mock_bot.send_voice.assert_called_once()
    assert mock_bot.send_voice.call_args[1]["chat_id"] == 12345
    assert mock_bot.send_voice.call_args[1]["caption"] == "Sample Voice Note"


@pytest.mark.asyncio
async def test_send_voice_with_fallback_missing_file():
    mock_bot = AsyncMock()
    result = await send_voice_with_fallback(
        bot=mock_bot,
        chat_id=12345,
        audio_path="/non/existent/path.wav",
        caption="Sample",
    )
    assert result is False
    mock_bot.send_voice.assert_not_called()


@pytest.mark.asyncio
async def test_process_workflow_turn_sends_voice_note(tmp_path: Path):
    clarify_audio = tmp_path / "clarify.wav"
    clarify_audio.write_bytes(b"RIFF dummy audio")

    mock_bot = AsyncMock()
    mock_message = MagicMock(spec=Message)
    mock_chat = MagicMock(spec=Chat)
    mock_chat.id = 9999
    mock_message.chat = mock_chat
    mock_message.answer = AsyncMock()

    state: ConsumerDostState = {
        "telegram_user_id": "test_tg_user",
        "chat_id": "9999",
        "thread_id": "thread_test",
        "status": "AWAITING_CLARIFICATION",
        "clarification_prompt": "Please provide your Order ID.",
        "clarification_audio_path": str(clarify_audio),
    }

    with patch("consumerdost.telegram.bot.get_compiled_graph") as mock_get_graph:
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = state
        mock_get_graph.return_value = mock_graph

        await process_workflow_turn(mock_bot, mock_message, state)

        # Verify chat actions and voice message
        mock_bot.send_chat_action.assert_any_call(chat_id="9999", action=ChatAction.TYPING)
        mock_bot.send_chat_action.assert_any_call(chat_id="9999", action=ChatAction.RECORD_VOICE)
        mock_bot.send_voice.assert_called_once()
        mock_message.answer.assert_called_once()
