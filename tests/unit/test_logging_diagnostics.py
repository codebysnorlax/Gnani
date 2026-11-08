import logging
from pathlib import Path
from loguru import logger
from saarthi.logging_config import (
    configure_logging,
    redact_sensitive_text,
    is_ai_error,
    is_system_error,
)


def test_redact_sensitive_text_credentials_and_pii():
    sample = (
        "Telegram token 1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 and "
        "Gemini key AIzaSyD-739182390182390182390182390182 and "
        "Groq key gsk_1234567890abcdef1234567890 and "
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token and "
        "Card 4111 2222 3333 4444 and "
        "Aadhaar 2345 6789 0123 and "
        "Email rohan.sharma@example.com and "
        "Phone 9876543210."
    )
    redacted = redact_sensitive_text(sample)

    assert "1234567890:ABC-DEF" not in redacted
    assert "[REDACTED_TELEGRAM_TOKEN]" in redacted
    assert "AIzaSyD" not in redacted
    assert "[REDACTED_GEMINI_KEY]" in redacted
    assert "gsk_12345" not in redacted
    assert "[REDACTED_GROQ_KEY]" in redacted
    assert "Bearer [REDACTED_TOKEN]" in redacted
    assert "4111 2222 3333 4444" not in redacted
    assert "[REDACTED_CARD]" in redacted
    assert "2345 6789 0123" not in redacted
    assert "[REDACTED_AADHAAR]" in redacted
    assert "rohan.sharma@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "9876543210" not in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_logging_sink_routing_and_file_creation(tmp_path: Path):
    logs_dir = tmp_path / "logs"
    configure_logging(logs_dir=logs_dir)

    ai_logger = logging.getLogger("saarthi.speech.gnani_stt")
    sys_logger = logging.getLogger("saarthi.database.engine")
    app_logger = logging.getLogger("saarthi.general")

    # 1. AI error log
    ai_logger.error("AI failure: token=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 failed for 9876543210")

    # 2. System error log
    sys_logger.error("System DB error: Connection lost to sqlite")

    # 3. Operational info log
    app_logger.info("Operational event: Case processed for user.")

    # Flush logger sinks
    logger.remove()

    # Check files created
    ai_err_file = logs_dir / "ai-err.log"
    sys_err_file = logs_dir / "system-err.log"
    app_file = logs_dir / "app.log"
    other_file = logs_dir / "other.log"

    assert ai_err_file.exists(), "ai-err.log was not created"
    assert sys_err_file.exists(), "system-err.log was not created"
    assert app_file.exists(), "app.log was not created"
    assert other_file.exists(), "other.log was not created"

    ai_content = ai_err_file.read_text(encoding="utf-8")
    assert "AI failure" in ai_content
    # Confirm redaction in log file
    assert "1234567890:ABC-DEF" not in ai_content
    assert "[REDACTED_TELEGRAM_TOKEN]" in ai_content
    assert "9876543210" not in ai_content
    assert "[REDACTED_PHONE]" in ai_content

    sys_content = sys_err_file.read_text(encoding="utf-8")
    assert "System DB error" in sys_content
    assert "AI failure" not in sys_content

    app_content = app_file.read_text(encoding="utf-8")
    assert "Operational event" in app_content


import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message, Chat, User as TelegramUser


@pytest.mark.asyncio
async def test_error_boundary_does_not_leak_trace_to_user():
    from saarthi.telegram.bot import process_workflow_turn

    mock_bot = AsyncMock()
    mock_message = AsyncMock(spec=Message)
    mock_message.chat = Chat(id=12345, type="private")
    mock_message.from_user = TelegramUser(id=12345, is_bot=False, first_name="Rohan")
    mock_message.answer = AsyncMock()

    state = {
        "telegram_user_id": "12345",
        "chat_id": "12345",
        "status": "DRAFT",
    }

    # Simulate an unexpected internal failure inside get_compiled_graph
    with patch("saarthi.telegram.bot.get_compiled_graph", side_effect=RuntimeError("Secret internal database crash at /secret/path/db.sqlite")):
        await process_workflow_turn(mock_bot, mock_message, state)

    mock_message.answer.assert_called_once()
    user_reply = mock_message.answer.call_args[0][0]
    # Verify no internal exception trace or file path leaked
    assert "Secret internal database crash" not in user_reply
    assert "/secret/path" not in user_reply
    assert "Traceback" not in user_reply
    assert "An error occurred" in user_reply

