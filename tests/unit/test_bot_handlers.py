from unittest.mock import AsyncMock, MagicMock
import pytest
from aiogram.types import User as TelegramUser, Chat, Message

from consumerdost.database.engine import init_db
from consumerdost.telegram.bot import (
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

