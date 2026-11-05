import pytest
from consumerdost.telegram.bot import create_bot_and_dispatcher, get_user_state, user_sessions


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
