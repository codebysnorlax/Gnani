import io
import re
import asyncio
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    TelegramObject,
    FSInputFile,
    BotCommand,
    ReplyKeyboardRemove,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.methods.base import TelegramMethod, TelegramType
from aiogram.exceptions import TelegramServerError, TelegramNetworkError, TelegramBadRequest
from aiogram.utils.chat_action import ChatActionSender

from saarthi.config import settings
from saarthi.database.engine import AsyncSessionLocal, init_db
from saarthi.database.repository import DisputeRepository
from saarthi.agent.state import ConsumerDostState
from saarthi.agent.graph import get_compiled_graph, run_atomic_generation
from saarthi.agent.response_composer import ResponseComposer
from saarthi.speech.gnani_tts import tts_service, SUPPORTED_INDIC_LANGUAGES
from saarthi.speech.gnani_stt import detect_indic_script_language
from saarthi.agent.voice_prompts import VoicePromptComposer, get_voice_gender
from saarthi.telegram.keyboards import (
    get_welcome_keyboard,
    get_confirmation_keyboard,
    get_dossier_action_keyboard,
    get_language_keyboard,
    get_resume_session_keyboard,
    get_persistent_menu_keyboard,
    get_voice_character_keyboard,
    get_neurons_keyboard,
    get_slot_confirmation_keyboard,
)
from saarthi.telegram.formatters import (
    format_welcome_message,
    format_assessment_card,
    format_cover_email,
    format_next_steps_card,
)

logger = logging.getLogger(__name__)

# Active session cache per user: user_id -> ConsumerDostState
user_sessions: dict[str, ConsumerDostState] = {}

NEURONS_KEY_TO_MODEL = {
    "super_vl": "nvidia/nemotron-3.5-super-vl:free",
    "north_mini": "cohere/north-mini-code:free",
    "nano_omni": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "standard": "standard",
    "auto": "auto",
}

NEURONS_MODEL_TO_NAME = {
    "nvidia/nemotron-3.5-super-vl:free": "Nemotron 3.5 Super VL",
    "cohere/north-mini-code:free": "North Mini Code",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "Nemotron 3 Nano Omni 30B",
    "standard": "Standard Engine (Offline / No LLM)",
    "auto": "Auto (Cascade & Fallback)",
}

_cached_banner_file_id: str | None = None


async def send_banner_safe(
    bot: Bot,
    chat_id: int | str,
    message: Message | None = None,
) -> None:
    """Send welcome banner image safely using cached Telegram file_id with strict timeout.
    
    Prevents photo upload stalls from blocking user interactions.
    """
    global _cached_banner_file_id
    banner_path = getattr(settings, "banner_image_path", settings.assets_dir / "banner.jpg")
    if not banner_path.exists():
        return
    try:
        photo_to_send = _cached_banner_file_id if _cached_banner_file_id else FSInputFile(str(banner_path))
        if message and hasattr(message, "answer_photo"):
            msg = await asyncio.wait_for(
                message.answer_photo(photo=photo_to_send),
                timeout=5.0,
            )
        else:
            msg = await asyncio.wait_for(
                bot.send_photo(chat_id=chat_id, photo=photo_to_send),
                timeout=5.0,
            )
        if msg and getattr(msg, "photo", None) and not _cached_banner_file_id:
            _cached_banner_file_id = msg.photo[-1].file_id
            logger.info(f"Cached Telegram banner file_id: {_cached_banner_file_id}")
    except Exception as e:
        logger.warning(f"Could not send welcome banner to {chat_id}: {e}")


async def send_voice_with_fallback(
    bot: Bot,
    chat_id: int | str,
    audio_path: str | Path | None,
    caption: str | None = None,
) -> bool:
    """Send voice message to chat if file exists, logging warning on failure with a timeout guard."""
    if audio_path and Path(audio_path).exists():
        try:
            voice_file = FSInputFile(str(audio_path))
            await asyncio.wait_for(
                bot.send_voice(chat_id=chat_id, voice=voice_file, caption=caption),
                timeout=10.0,
            )
            return True
        except Exception as e:
            logger.warning(f"Could not send voice note to {chat_id}: {e}")
    return False


FIELD_KEY_MAP = {
    "brand": "brand_raw",
    "amount": "amount_paid_inr",
    "order_id": "order_id",
    "incident_date": "incident_date",
    "full_name": "complainant_full_name",
}


async def confirm_and_advance_slot(
    bot: Bot,
    message: Message,
    state: ConsumerDostState,
    field: str,
    user_id: str,
) -> None:
    """Commit confirmed slot value into state and route to next missing field or assessment."""
    chat_id = str(message.chat.id)
    val = state.get("pending_confirmation_value")
    state_key = FIELD_KEY_MAP.get(field, field)
    if val is not None:
        state[state_key] = val

    state["pending_confirmation_field"] = None
    state["pending_confirmation_value"] = None
    state["clarification_target_field"] = None

    # Re-evaluate missing fields
    missing = []
    if not state.get("brand_raw"):
        missing.append("brand")
    if state.get("amount_paid_inr") is None or state.get("amount_paid_inr") <= 0:
        missing.append("amount")
    if not state.get("incident_date"):
        missing.append("incident_date")
    if not state.get("order_id"):
        missing.append("order_id")
    if not state.get("complainant_full_name"):
        missing.append("full_name")
    state["missing_fields"] = missing

    if not missing:
        from saarthi.agent.nodes import node_resolve
        resolve_res = await node_resolve(state)
        state.update(resolve_res)
        state["status"] = "AWAITING_CONFIRMATION"
        await save_user_state(user_id, state)

        assessment_audio = state.get("assessment_audio_path")
        async with ChatActionSender.upload_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=assessment_audio,
                caption="<b>Dispute Assessment Walkthrough:</b> Statutory claim summary.",
            )
        card = format_assessment_card(state)
        await message.answer(card, reply_markup=get_confirmation_keyboard())
    else:
        from saarthi.agent.nodes import node_clarify
        clarify_res = await node_clarify(state)
        state.update(clarify_res)
        state["status"] = "AWAITING_CLARIFICATION"
        await save_user_state(user_id, state)

        engine = state.get("llm_engine") or "Standard Engine"
        clarify_audio = state.get("clarification_audio_path")
        async with ChatActionSender.upload_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=clarify_audio,
                caption=f"<b>Voice Clarification ({engine}):</b> Please listen to the details needed.",
            )
        prompt = state.get("clarification_prompt")
        if state.get("pending_confirmation_field"):
            kb = get_slot_confirmation_keyboard(state["pending_confirmation_field"])
            await message.answer(prompt, reply_markup=kb)
        else:
            await message.answer(prompt)


async def setup_bot_commands(bot: Bot) -> None:
    """Register menu commands with Telegram so they appear in the input box menu."""
    commands = [
        BotCommand(command="start", description="Start SAARTHI assistance"),
        BotCommand(command="neurons", description="Neurons AI model / AI मॉडल चुनें"),
        BotCommand(command="lang", description="Choose language / भाषा चुनें"),
        BotCommand(command="gender", description="Choose voice & gender / आवाज़ और लिंग चुनें"),
        BotCommand(command="newdispute", description="Start fresh dispute session"),
        BotCommand(command="mycases", description="View past dispute cases"),
        BotCommand(command="privacy", description="Purge personal data"),
    ]
    try:
        from aiogram.types import (
            BotCommandScopeDefault,
            BotCommandScopeAllPrivateChats,
            MenuButtonCommands,
        )
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
        for lang in ["en", "hi"]:
            await bot.set_my_commands(commands, scope=BotCommandScopeDefault(), language_code=lang)
            await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats(), language_code=lang)
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Registered Telegram input box menu commands: /start, /neurons, /lang, /gender across scopes and languages.")
    except Exception as e:
        logger.warning(f"Failed to register Telegram bot commands: {e}")


async def get_or_create_welcome_voice(lang: str = "hi-IN", voice: str = "Shivani") -> Path | None:
    """Get cached welcome audio or synthesize a new one using Timbre v3.0."""
    cache_dir = settings.data_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"welcome_{lang}_{voice}.wav"
    if cache_path.exists():
        return cache_path

    script = VoicePromptComposer.compose_welcome(lang, voice=voice)
    return await tts_service.synthesize_speech(
        text=script,
        output_path=cache_path,
        language=lang,
        voice=voice,
        model="timbre-v3.0",
    )


class DeduplicationMiddleware(BaseMiddleware):
    """Prevents duplicate processing of Telegram updates on retries."""
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        update_id = getattr(event, "update_id", None)
        user = getattr(event, "from_user", None)
        user_id = str(user.id) if user else "system"

        if update_id is not None:
            async with AsyncSessionLocal() as session:
                repo = DisputeRepository(session)
                if await repo.is_update_processed(str(update_id)):
                    logger.info(f"Duplicate update {update_id} skipped")
                    return None
                await repo.mark_update_processed(str(update_id), user_id)

        return await handler(event, data)


async def get_or_create_user_state(user_id: str, chat_id: str) -> ConsumerDostState:
    """Retrieve durable user session state from SQLite, or initialize default draft."""
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        user_record = await repo.get_or_create_user(user_id, chat_id)
        saved_lang = user_record.preferred_language or "hi-IN"
        saved_voice = getattr(user_record, "preferred_voice_character", "Shivani") or "Shivani"

        state = await repo.load_session_state(user_id)
        if state is None:
            state = {
                "telegram_user_id": user_id,
                "chat_id": chat_id,
                "thread_id": f"thread_{user_id}",
                "preferred_language": saved_lang,
                "preferred_voice_character": saved_voice,
                "status": "DRAFT",
            }
            await repo.save_session_state(user_id, state)
        else:
            state.setdefault("preferred_language", saved_lang)
            state["preferred_voice_character"] = saved_voice
        user_sessions[user_id] = state
        return state


async def save_user_state(user_id: str, state: ConsumerDostState) -> None:
    """Persist session state to SQLite."""
    user_sessions[user_id] = state
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        await repo.save_session_state(user_id, state)


async def clear_user_state(user_id: str) -> None:
    """Clear session state from SQLite."""
    user_sessions.pop(user_id, None)
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        await repo.clear_session_state(user_id)


def get_user_state(user_id: str, chat_id: str) -> ConsumerDostState:
    """Synchronous fallback helper for backward compatibility."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "telegram_user_id": user_id,
            "chat_id": chat_id,
            "thread_id": f"thread_{user_id}",
            "preferred_language": "hi-IN",
            "status": "DRAFT",
        }
    return user_sessions[user_id]


class TelegramRetryMiddleware(BaseRequestMiddleware):
    """Retries transient Telegram server errors (502 Bad Gateway, 504 Timeout) on outbound requests,
    and strips formatting if Telegram entity parsing fails.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> TelegramType:
        for attempt in range(1, self.max_retries + 1):
            try:
                return await make_request(bot, method)
            except TelegramBadRequest as e:
                err_msg = str(e).lower()
                if "can't parse entities" in err_msg or "unsupported start tag" in err_msg or "entity" in err_msg:
                    logger.warning(
                        f"Telegram entity parse failed on {type(method).__name__}: {e}. Retrying with plain text."
                    )
                    if hasattr(method, "parse_mode"):
                        method.parse_mode = None
                    if hasattr(method, "text") and isinstance(method.text, str):
                        method.text = re.sub(r"<[^>]+>", "", method.text)
                    if hasattr(method, "caption") and isinstance(method.caption, str):
                        method.caption = re.sub(r"<[^>]+>", "", method.caption)
                    return await make_request(bot, method)
                raise
            except (TelegramServerError, TelegramNetworkError) as e:
                err_text = str(e).lower()
                is_timeout = "timeout" in err_text or "time out" in err_text
                if attempt == self.max_retries or (is_timeout and attempt >= 2):
                    raise
                logger.warning(
                    f"Telegram request {type(method).__name__} failed ({e}). Retrying in {self.retry_delay * attempt:.1f}s (attempt {attempt}/{self.max_retries})..."
                )
                await asyncio.sleep(self.retry_delay * attempt)


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    bot.session.middleware(TelegramRetryMiddleware())
    dp = Dispatcher()
    dp.update.middleware(DeduplicationMiddleware())

    # 1. Command Handlers
    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            user_record = await repo.get_or_create_user(user_id, chat_id)
            saved_lang = user_record.preferred_language or "hi-IN"
            saved_voice = getattr(user_record, "preferred_voice_character", "Shivani") or "Shivani"
            has_seen_banner = bool(getattr(user_record, "has_seen_banner", 0))
            existing_state = await repo.load_session_state(user_id)

        # Check for unfinalized active dispute to offer session recovery
        if existing_state and existing_state.get("status") in ("AWAITING_CONFIRMATION", "AWAITING_CLARIFICATION"):
            claim_amt = (
                existing_state.get("total_claim_paise", 0) / 100.0
                if existing_state.get("total_claim_paise")
                else existing_state.get("amount_paid_inr", 0.0)
            )
            brand = (existing_state.get("brand_resolved") or {}).get(
                "corporate_name", existing_state.get("brand_raw", "Dispute")
            )
            await message.answer(
                f"<b>Previous Dispute Found:</b>\n"
                f"You have an ongoing dispute for <b>{brand}</b> (₹{claim_amt:,.2f}).\n\n"
                f"Status: <code>{existing_state.get('status')}</code>\n"
                f"Would you like to resume where you left off, or start fresh?",
                reply_markup=get_resume_session_keyboard(),
            )
            return

        # Initialize fresh draft in SQLite
        fresh_state = {
            "telegram_user_id": user_id,
            "chat_id": chat_id,
            "thread_id": f"thread_{user_id}",
            "preferred_language": saved_lang,
            "preferred_voice_character": saved_voice,
            "status": "DRAFT",
        }
        await save_user_state(user_id, fresh_state)

        # Always send banner image on /start (initial start or when user clears chat and starts from scratch)
        await send_banner_safe(bot, chat_id, message=message)
        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            await repo.mark_banner_seen(user_id)

        # Show record_voice chat action
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)

        # 1. Voice-first greeting
        welcome_voice = await get_or_create_welcome_voice(saved_lang, voice=saved_voice)
        await send_voice_with_fallback(
            bot=bot,
            chat_id=chat_id,
            audio_path=welcome_voice,
            caption="<b>SAARTHI:</b> Voice Grievance Assistant (Gnani Timbre v3.0)",
        )

        # 2. Companion text with interactive menu options (Language, Voice, AI Neurons)
        await message.answer(
            format_welcome_message(),
            reply_markup=get_welcome_keyboard(),
        )

    @dp.callback_query(F.data == "session:resume")
    async def handle_session_resume(callback: CallbackQuery):
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        status = state.get("status")

        if status == "AWAITING_CONFIRMATION":
            assessment_audio = state.get("assessment_audio_path")
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=assessment_audio,
                caption="<b>Dispute Assessment Walkthrough:</b> Statutory claim summary.",
            )
            card = format_assessment_card(state)
            await callback.message.answer(card, reply_markup=get_confirmation_keyboard())
        elif status == "AWAITING_CLARIFICATION":
            clarify_audio = state.get("clarification_audio_path")
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=clarify_audio,
                caption="<b>Voice Clarification:</b> Please listen to the details needed.",
            )
            prompt = state.get("clarification_prompt", "Please provide missing order or name details.")
            await callback.message.answer(prompt)
        else:
            await callback.message.answer(
                "<b>Resuming your case:</b> Please speak or type your grievance update to proceed."
            )
        await callback.answer()

    @dp.callback_query(F.data == "session:reset")
    async def handle_session_reset(callback: CallbackQuery):
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        await clear_user_state(user_id)
        fresh_state = {
            "telegram_user_id": user_id,
            "chat_id": chat_id,
            "thread_id": f"thread_{user_id}",
            "preferred_language": "hi-IN",
            "preferred_voice_character": "Shivani",
            "status": "DRAFT",
        }
        await save_user_state(user_id, fresh_state)

        # Send banner when user starts from scratch
        await send_banner_safe(bot, chat_id, message=callback.message)

        await callback.message.answer(
            "Previous case cleared. Please speak or type your consumer dispute to begin, or select from the options below:",
            reply_markup=get_welcome_keyboard(),
        )
        await callback.answer()

    @dp.message(F.text == "Language / भाषा")
    @dp.message(Command("lang"))
    @dp.message(Command("language"))
    async def cmd_language(message: Message):
        await message.answer(
            "<b>Select Preferred Language / अपनी भाषा चुनें:</b>\n"
            "SAARTHI speaks and understands 10 Indian languages via Gnani Speech AI.",
            reply_markup=get_language_keyboard(),
        )

    @dp.message(F.text == "Voice / आवाज़")
    @dp.message(F.text == "Voice / आवाज")
    @dp.message(Command("gender"))
    @dp.message(Command("voice"))
    async def cmd_voice(message: Message):
        await message.answer(
            "<b>Select Voice Character & Gender / आवाज़ और लिंग चुनें:</b>\n"
            "Choose a voice character for spoken walkthroughs and updates:",
            reply_markup=get_voice_character_keyboard(),
        )

    @dp.message(F.text == "Neurons / AI मॉडल")
    @dp.message(F.text == "Neurons")
    @dp.message(F.text == "/neurons")
    @dp.message(Command("neurons"))
    async def cmd_neurons(message: Message):
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        curr = state.get("neurons_model") or "auto"
        curr_name = NEURONS_MODEL_TO_NAME.get(curr, curr)
        await message.answer(
            "<b>Select Neurons AI Model / AI मॉडल चुनें:</b>\n\n"
            "Choose which OpenRouter free model to power the SAARTHI brain:\n"
            "1. <b>Nemotron 3.5 Super VL</b>: Fast multimodal language reasoning.\n"
            "2. <b>North Mini Code</b>: Precise instruction adherence and structuring.\n"
            "3. <b>Nemotron 3 Nano Omni 30B</b>: Deep reasoning.\n"
            "4. <b>Auto</b>: Dynamically cascades across all models, falling back automatically if any model is rate-limited or unavailable.\n\n"
            f"<b>Active Model:</b> <code>{curr_name}</code>",
            reply_markup=get_neurons_keyboard(curr),
        )

    @dp.message(Command("newdispute"))
    @dp.message(Command("cancel"))
    async def cmd_new_dispute(message: Message):
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        await clear_user_state(user_id)
        fresh_state = {
            "telegram_user_id": user_id,
            "chat_id": chat_id,
            "thread_id": f"thread_{user_id}",
            "preferred_language": "hi-IN",
            "preferred_voice_character": "Shivani",
            "status": "DRAFT",
        }
        await save_user_state(user_id, fresh_state)

        await send_banner_safe(bot, chat_id, message=message)

        await message.answer(
            "Previous session cleared. Please speak or type your consumer dispute to begin, or select from the options below:",
            reply_markup=get_welcome_keyboard(),
        )

    @dp.message(Command("mycases"))
    async def cmd_my_cases(message: Message):
        user_id = str(message.from_user.id)
        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            cases = await repo.get_user_cases(user_id)

        if not cases:
            await message.answer("You have not generated any dispute cases yet. Send a voice note or /start to begin.")
            return

        lines = ["<b>Your Past Consumer Disputes:</b>\n"]
        for c in cases:
            lines.append(
                f"• <b>{c.id}</b> | {c.brand_name} | {c.incident_date}\n"
                f"  Total Demand: ₹{c.total_demanded_paise / 100:,.2f} | Status: <code>{c.status}</code>"
            )
        await message.answer("\n\n".join(lines))

    @dp.message(Command("privacy"))
    async def cmd_privacy(message: Message):
        user_id = str(message.from_user.id)
        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            deleted = await repo.delete_user_data(user_id)

        await clear_user_state(user_id)
        await message.answer(
            f"<b>Data Deleted:</b> {deleted} dispute records and personal data have been completely purged from SQLite."
        )

    # 2. Callback Query Handlers
    @dp.callback_query(F.data == "menu:language")
    async def handle_menu_language(callback: CallbackQuery):
        await callback.message.answer(
            "<b>Select Preferred Language / अपनी भाषा चुनें:</b>",
            reply_markup=get_language_keyboard(),
        )
        await callback.answer()

    @dp.callback_query(F.data == "menu:voice")
    async def handle_menu_voice(callback: CallbackQuery):
        await callback.message.answer(
            "<b>Select Voice Character / आवाज़ चुनें:</b>",
            reply_markup=get_voice_character_keyboard(),
        )
        await callback.answer()

    @dp.callback_query(F.data == "menu:neurons")
    async def handle_menu_neurons(callback: CallbackQuery):
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        curr = state.get("neurons_model") or "auto"
        curr_name = NEURONS_MODEL_TO_NAME.get(curr, curr)
        await callback.message.answer(
            "<b>Select Neurons AI Model / AI मॉडल चुनें:</b>\n\n"
            "Choose which model powers the SAARTHI brain:\n"
            "1. <b>Nemotron 3.5 Super VL</b>: Fast multimodal language reasoning.\n"
            "2. <b>North Mini Code</b>: Precise instruction adherence and structuring.\n"
            "3. <b>Nemotron 3 Nano Omni 30B</b>: Deep reasoning.\n"
            "4. <b>Standard Engine</b>: Offline rule-based engine (instant, zero external LLM dependencies).\n"
            "5. <b>Auto</b>: Dynamically cascades across all models, falling back automatically if any model is rate-limited or unavailable.\n\n"
            f"<b>Active Model:</b> <code>{curr_name}</code>",
            reply_markup=get_neurons_keyboard(curr),
        )
        await callback.answer()

    @dp.callback_query(F.data.startswith("voice:"))
    async def handle_voice_select(callback: CallbackQuery):
        selected_voice = callback.data.split(":")[1]
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        state["preferred_voice_character"] = selected_voice
        await save_user_state(user_id, state)

        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            await repo.update_user_profile(user_id, preferred_voice_character=selected_voice)

        gender = get_voice_gender(selected_voice)
        gender_label = "Female / महिला" if gender == "female" else "Male / पुरुष"
        lang = state.get("preferred_language", "hi-IN")

        # Synthesize audio preview in selected voice & gender
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
        preview_text = (
            f"Namaste! Main {selected_voice} hoon. <pauses> Maine aapka voice character save kar liya hai."
            if lang.startswith("hi") else
            f"Hello! I am {selected_voice}. <pauses> Your voice preference has been saved."
        )
        preview_path = settings.data_dir / "cache" / f"voice_preview_{selected_voice}_{lang}.wav"
        preview_audio = await tts_service.synthesize_speech(
            text=preview_text,
            output_path=preview_path,
            language=lang,
            voice=selected_voice,
            model="timbre-v3.0",
        )
        if preview_audio and preview_audio.exists():
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=preview_audio,
                caption=f"<b>Voice set to {selected_voice} ({gender_label}).</b>",
            )

        await callback.message.answer(
            f"<b>Voice character set to {selected_voice} ({gender_label}).</b>\n"
            "Subsequent voice summaries will use this voice and gender."
        )
        await callback.answer()

    @dp.callback_query(F.data.startswith("neurons:"))
    async def handle_neurons_select(callback: CallbackQuery):
        key = callback.data.split("neurons:")[1]
        model_id = NEURONS_KEY_TO_MODEL.get(key, "auto")
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        state["neurons_model"] = model_id
        await save_user_state(user_id, state)

        model_name = NEURONS_MODEL_TO_NAME.get(model_id, model_id)
        if callback.message:
            await callback.message.edit_text(
                "<b>Neurons AI Model Updated:</b>\n\n"
                f"Active Model: <code>{model_name}</code>\n\n"
                "SAARTHI will use this model for entity extraction and dynamic conversation. "
                "If the selected model encounters rate limits, it will automatically fallback to ensure uninterrupted guidance.",
                reply_markup=get_neurons_keyboard(model_id),
            )
        await callback.answer(f"Selected: {model_name}")

    @dp.callback_query(F.data.startswith("lang:"))
    async def handle_language_select(callback: CallbackQuery):
        selected_lang = callback.data.split(":")[1]
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        state["preferred_language"] = selected_lang
        await save_user_state(user_id, state)

        lang_name = SUPPORTED_INDIC_LANGUAGES.get(selected_lang, selected_lang)
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)

        # Generate localized voice greeting in chosen language and voice
        voice = state.get("preferred_voice_character") or "Shivani"
        voice_path = await get_or_create_welcome_voice(selected_lang, voice=voice)
        await send_voice_with_fallback(
            bot=bot,
            chat_id=chat_id,
            audio_path=voice_path,
            caption=f"<b>Language updated to {lang_name}</b>",
        )

        await callback.message.answer(
            f"<b>Language set to {lang_name}.</b>\n"
            "You can now speak or type your consumer complaint in your preferred language."
        )
        await callback.answer()


    @dp.callback_query(F.data == "action:generate_bundle")
    async def handle_generate_bundle(callback: CallbackQuery):
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)

        # Ensure incomplete cases remain in clarification without generating documents
        if state.get("status") != "AWAITING_CONFIRMATION" or state.get("missing_fields"):
            prompt = state.get("clarification_prompt") or "Please provide missing grievance details before generating documents."
            await callback.message.answer(
                f"Action unavailable: Grievance details are incomplete.\n{prompt}"
            )
            await callback.answer()
            return

        await callback.message.answer("<i>Generating your complete Tri-Fold Escalation Dossier...</i>")

        # 1. Run atomic bundle and TTS generation via LangGraph
        try:
            async with ChatActionSender.record_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
                gen_res = await run_atomic_generation(state)
                state.update(gen_res)
                await save_user_state(user_id, state)
        except Exception as e:
            logger.exception(f"Bundle generation failed for user {user_id}: {e}")
            await callback.message.answer(
                "Unable to generate your document bundle at this moment. "
                "Please check your details and try again."
            )
            await callback.answer()
            return

        # 3. Save to database
        brand_info = state.get("brand_resolved") or {}
        case_ref = state.get("case_reference_id") or "SRTH-2026-0001"
        async with AsyncSessionLocal() as session:
            repo = DisputeRepository(session)
            await repo.create_dispute_case(
                case_id=case_ref,
                telegram_user_id=user_id,
                complainant_name=state.get("complainant_full_name") or "Consumer",
                complainant_contact=state.get("complainant_contact") or "Not Provided",
                brand_name=brand_info.get("canonical_name", state.get("brand_raw", "Brand")),
                brand_corporate_name=brand_info.get("corporate_name", "Corporate Vendor"),
                registered_address=brand_info.get("registered_address", "India"),
                nodal_email=brand_info.get("nodal_email", "support@brand.com"),
                order_id=state.get("order_id") or "N/A",
                incident_date=state.get("incident_date") or "2026-10-25",
                category=state.get("dispute_category") or "E_COMMERCE",
                issue_type=state.get("issue_type") or "ECOMMERCE_REFUND_DELAY_OR_DENIAL",
                principal_paise=state.get("principal_paise", 0),
                interest_paise=state.get("calculated_interest_paise", 0),
                statutory_penalty_paise=state.get("statutory_penalty_paise", 0),
                damages_demanded_paise=state.get("damages_claimed_paise", 0),
                total_demanded_paise=state.get("total_claim_paise", 0),
                narrative_facts_en=state.get("dispute_narrative_en") or "",
                legal_clauses=state.get("legal_clauses") or [],
                status="BUNDLE_GENERATED",
            )
            if state.get("pdf_file_path"):
                await repo.add_artifact(case_ref, "LEGAL_NOTICE_PDF", file_path=state["pdf_file_path"])
            if state.get("nch_dossier_text"):
                await repo.add_artifact(case_ref, "NCH_DOSSIER", content_text=state["nch_dossier_text"])
            if state.get("twitter_draft_text"):
                await repo.add_artifact(case_ref, "TWITTER_DRAFT", content_text=state["twitter_draft_text"])
            if state.get("tts_audio_path"):
                await repo.add_artifact(case_ref, "TTS_SUMMARY", file_path=state["tts_audio_path"])

        # 4. Deliver Document 1: PDF Attachment + Cover Email
        pdf_path = state.get("pdf_file_path")
        if pdf_path and Path(pdf_path).exists():
            async with ChatActionSender.upload_document(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
                pdf_file = FSInputFile(pdf_path, filename=f"Legal_Demand_Notice_{case_ref}.pdf")
                await callback.message.answer_document(
                    document=pdf_file,
                    caption=f"<b>Official Legal Notice:</b> {case_ref}\nServe this directly to the brand's statutory Nodal Officer.",
                )
            await callback.message.answer(format_cover_email(state))

        # 5. Deliver Document 2: NCH 1915 WhatsApp Dossier Block
        nch_text = state.get("nch_dossier_text")
        if nch_text:
            await callback.message.answer(
                f"<b>Document 2: National Consumer Helpline (NCH 1915) Dossier</b>\n\n"
                f"<pre>{nch_text}</pre>"
            )

        # 6. Deliver Document 3: Public Social Escalation Post (X)
        twitter_text = state.get("twitter_draft_text")
        if twitter_text:
            await callback.message.answer(
                f"<b>Document 3: Public Social Escalation Post (&lt;280 chars)</b>\n\n"
                f"<code>{twitter_text}</code>"
            )

        # 7. Deliver Document 4: Gnani Timbre TTS Voice Note
        tts_audio = state.get("tts_audio_path")
        async with ChatActionSender.upload_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=tts_audio,
                caption="<b>Spoken Voice Guide:</b> Action walkthrough in your preferred language.",
            )

        # 8. Interactive Action Buttons
        wa_url = state.get("nch_whatsapp_url", "https://wa.me/918860005372")
        tw_url = state.get("twitter_intent_url", "https://twitter.com")
        await callback.message.answer(
            "<b>Tri-Fold Escalation Dossier Complete</b>\n"
            "Use the buttons below to open NCH WhatsApp or post your public escalation post on X immediately:",
            reply_markup=get_dossier_action_keyboard(wa_url, tw_url),
        )
        await callback.message.answer(format_next_steps_card(state))
        await callback.answer()

    @dp.callback_query(F.data == "action:edit_details")
    async def handle_edit_details(callback: CallbackQuery):
        await callback.message.answer(
            "To update your details, please type your correction (for example:\n"
            "• <i>Change amount to 15499</i>\n"
            "• <i>My Order ID is OD99887766</i>\n"
            "• <i>Change date to 26 October</i>)"
        )
        await callback.answer()

    @dp.callback_query(F.data == "action:cancel")
    async def handle_cancel(callback: CallbackQuery):
        user_id = str(callback.from_user.id)
        await clear_user_state(user_id)
        await callback.message.answer("Dispute draft cancelled.")
        await callback.answer()

    @dp.callback_query(F.data.startswith("slot_confirm:"))
    async def handle_slot_confirm(callback: CallbackQuery):
        field = callback.data.split("slot_confirm:")[1]
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        await confirm_and_advance_slot(bot, callback.message, state, field, user_id)
        await callback.answer("Confirmed")

    @dp.callback_query(F.data.startswith("slot_edit:"))
    async def handle_slot_edit(callback: CallbackQuery):
        field = callback.data.split("slot_edit:")[1]
        user_id = str(callback.from_user.id)
        chat_id = str(callback.message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)
        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        state["pending_confirmation_field"] = None
        state["pending_confirmation_value"] = None
        state["clarification_target_field"] = field
        await save_user_state(user_id, state)
        await callback.message.answer("Send edit one (please send the corrected detail):")
        await callback.answer()

    # 3. Message Handlers (Voice and Text)
    @dp.message(F.voice)
    async def handle_voice_message(message: Message):
        # 60 second duration cap
        if message.voice.duration > 60:
            await message.answer("Voice note exceeds 60 seconds. Please send a shorter voice note or type your complaint.")
            return

        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)

        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await message.answer("<i>Listening and transcribing with Gnani Prisma v3.0 STT...</i>")

        # Download voice file
        file_obj = io.BytesIO()
        await bot.download(message.voice.file_id, destination=file_obj)
        state["voice_bytes"] = file_obj.getvalue()
        state["raw_input_text"] = None

        await process_workflow_turn(bot, message, state)

    @dp.message(F.text)
    async def handle_text_message(message: Message):
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        state = await get_or_create_user_state(user_id, chat_id)

        # Check for textual confirmation if a slot is awaiting confirmation
        if state.get("pending_confirmation_field"):
            raw_clean = (message.text or "").strip().lower()
            if raw_clean in {"confirm", "yes", "haan", "ha", "sahi", "sahi hai", "ok", "done", "confirm it", "theek hai", "theek"}:
                field = state["pending_confirmation_field"]
                await confirm_and_advance_slot(bot, message, state, field, user_id)
                return
            elif raw_clean in {"edit", "change", "badlo", "galat", "no", "nahi", "change it", "edit it"}:
                field = state["pending_confirmation_field"]
                state["pending_confirmation_field"] = None
                state["pending_confirmation_value"] = None
                state["clarification_target_field"] = field
                await save_user_state(user_id, state)
                await message.answer("Send edit one (please send the corrected detail):")
                return

        state["raw_input_text"] = message.text
        state["voice_bytes"] = None

        await process_workflow_turn(bot, message, state)

    return bot, dp


def is_conversational_greeting_or_help(text: str) -> bool:
    """Detect if user input is an introductory greeting, capability query, language query, or chit-chat."""
    if not text:
        return False
    clean = re.sub(r"[^\w\s]", "", text).strip().lower()
    common_phrases = {
        "hello", "hi", "hey", "hii", "heyy", "namaste", "namaskar",
        "good morning", "good evening", "good afternoon",
        "who are you", "who r u", "what is this", "what is saarthi",
        "help", "help me", "how to use", "how does this work",
        "kaise ho", "how are you", "kya haal hai", "kya haal",
    }
    if clean in common_phrases:
        return True

    # 1. Capability, identity, and assistance patterns
    inquiry_patterns = [
        r"\b(what|wat)\s+(can|ca|do)\s+you\s+do\b",
        r"\bwhat\s+(are\s+your\s+)?capabilities\b",
        r"\bhow\s+can\s+you\s+help(\s+me)?\b",
        r"\bwho\s+are\s+you\b",
        r"\bwhat\s+is\s+saarthi\b",
        r"\bkya\s+(kuch\s+)?kar\s+sakte\s+ho\b",
        r"\baap\s+kya\s+karte\s+ho\b",
        r"\btum\s+kya\s+karte\s+ho\b",
        r"\baap\s+kaun\s+ho\b",
        r"\btum\s+kaun\s+ho\b",
        r"\bmadad\s+kaise\s+(karein|karoge)\b",
    ]
    for pattern in inquiry_patterns:
        if re.search(pattern, clean):
            return True

    # 2. Language support and capability queries
    lang_patterns = [
        r"\b(which|what|how\s+many)\s+.*(lang|language|languages|bhasha|bhashayein|boli)\b",
        r"\b(lang|language|languages|bhasha|bhashayein|boli)\s+.*(support|supported|know|speak|available)\b",
        r"\b(can|do)\s+you\s+(support|speak|know|understand)\s+.*(language|languages|hindi|english|kannada|tamil|telugu|marathi|bengali|gujarati|malayalam|punjabi|hinglish|bhasha)\b",
        r"\b(support|supported)\s+(language|languages)\b",
        r"\b(konsi|kon\s+si|kitni)\s+bhasha\b",
        r"\bwhich\s+(all\s+)?languages?\b",
        r"\bwhat\s+all\s+languages?\b",
    ]
    for pattern in lang_patterns:
        if re.search(pattern, clean):
            return True

    # 3. Conversational questions that lack consumer dispute or transaction facts
    dispute_keywords = {
        "order", "refund", "return", "cancelled", "cancel", "delivery", "delivered",
        "defective", "damaged", "broken", "bought", "purchased", "payment", "paid",
        "rupees", "rs", "inr", "paise", "flight", "ticket", "airline", "bank",
        "charge", "charged", "account", "flipkart", "amazon", "zomato", "swiggy",
        "myntra", "meesho", "fraud", "scam", "cheat", "nodal", "penalty", "interest",
    }
    words = set(clean.split())
    has_dispute_context = bool(words.intersection(dispute_keywords))

    if not has_dispute_context:
        is_question = "?" in text or bool(re.search(r"^(who|what|why|how|when|which|can|could|do|does|is|are|tell me|kya|kaise|kaun)\b", clean))
        if is_question:
            return True

    return False


async def handle_conversational_inquiry(bot: Bot, message: Message, state: ConsumerDostState) -> None:
    """Respond dynamically to greetings, capabilities, and language inquiries via the Neurons Router Brain."""
    chat_id = str(message.chat.id)
    raw_text = state.get("raw_input_text") or getattr(message, "text", None) or ""
    voice_char = state.get("preferred_voice_character") or "Shivani"
    neurons_model = state.get("neurons_model")

    detected = detect_indic_script_language(raw_text)
    is_english = (detected == "en-IN") or bool(re.search(r"^[a-zA-Z0-9\s\.,\?!'-]+$", raw_text))
    lang = "en-IN" if is_english else (state.get("preferred_language") or "hi-IN")

    # 1. Dynamic LLM composition with continuous typing action in Telegram title header
    is_initial = not bool(
        state.get("brand_raw")
        or state.get("amount_paid_inr")
        or state.get("has_greeted")
        or state.get("status") in {"DRAFT", "AWAITING_CLARIFICATION", "AWAITING_CONFIRMATION"}
    )
    async with ChatActionSender.typing(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
        composed = await ResponseComposer.compose_conversation(
            user_text=raw_text,
            language=lang,
            voice_character=voice_char,
            preferred_model=neurons_model,
            is_initial_turn=is_initial,
        )
    state["has_greeted"] = True

    # 2. Synthesize complete spoken voice note with continuous record_voice action
    import hashlib
    h = hashlib.md5(f"{raw_text}_{lang}_{voice_char}".encode()).hexdigest()[:8]
    cache_path = settings.data_dir / "cache" / f"conv_{lang}_{voice_char}_{h}.wav"
    audio_path = None
    try:
        async with ChatActionSender.record_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            audio_path = await tts_service.synthesize_speech(
                text=composed.spoken_text,
                output_path=cache_path,
                language=lang,
                voice=voice_char,
                model="timbre-v3.0",
            )
    except Exception as e:
        logger.warning(f"Voice synthesis for conversational inquiry failed: {e}")

    # 3. Send voice note with continuous upload_voice action
    if audio_path and audio_path.exists():
        async with ChatActionSender.upload_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=audio_path,
                caption=f"<b>SAARTHI ({composed.engine}):</b> Spoken by {voice_char}",
            )

    # 4. Companion HTML message with interactive keyboard options
    await message.answer(
        composed.visible_text,
        reply_markup=get_welcome_keyboard(),
    )
    state["status"] = "DRAFT"
    user_id = state.get("telegram_user_id") or (str(message.from_user.id) if getattr(message, "from_user", None) else "")
    if user_id:
        await save_user_state(user_id, state)


async def process_workflow_turn(bot: Bot, message: Message, state: ConsumerDostState) -> None:
    """Run LangGraph pipeline turn and reply with voice-first clarification or assessment card."""
    chat_id = str(message.chat.id)

    # Check for friendly greetings or capability inquiries before entering legal intake
    raw_text = state.get("raw_input_text") or getattr(message, "text", None) or ""
    if not state.get("brand_raw") and not state.get("amount_paid_inr"):
        if is_conversational_greeting_or_help(raw_text):
            await handle_conversational_inquiry(bot, message, state)
            return

    had_voice = bool(state.get("voice_bytes"))

    # Live progress reporter in chat
    status_msg = None
    try:
        status_msg = await bot.send_message(chat_id=chat_id, text="Connecting to Neurons Nano...")
    except Exception as e:
        logger.debug(f"Could not send live progress status message: {e}")

    last_status_text = "Connecting to Neurons Nano..."

    async def report_progress(text: str) -> None:
        nonlocal last_status_text, status_msg
        if not status_msg or text == last_status_text:
            return
        last_status_text = text
        try:
            if hasattr(status_msg, "edit_text"):
                await status_msg.edit_text(text)
            else:
                await bot.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id, text=text)
        except Exception as e:
            logger.debug(f"Could not edit live progress message: {e}")

    async def cleanup_status_msg() -> None:
        nonlocal status_msg
        if status_msg:
            try:
                if hasattr(status_msg, "delete"):
                    await status_msg.delete()
                else:
                    await bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
            except Exception:
                pass
            status_msg = None

    state["progress_callback"] = report_progress

    try:
        async with ChatActionSender.typing(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            graph = await get_compiled_graph()
            result = await graph.ainvoke(state)
            state.update(result)
    except Exception as e:
        await cleanup_status_msg()
        logger.exception(f"Workflow turn execution failed: {e}")
        await message.answer(
            "An error occurred while analyzing your dispute details. "
            "Please try rephrasing or type /newdispute to restart."
        )
        return

    # Clean up live status message before presenting results
    await cleanup_status_msg()

    # Surface "What I Heard" STT confirmation card to confirm Prisma v3.0 transcription
    if had_voice:
        transcript = result.get("raw_input_text") or ""
        stt_ms = result.get("stt_latency_ms")
        timing_str = f" ({stt_ms}ms)" if stt_ms else ""
        await message.answer(
            f"<b>What I Heard:</b>\n"
            f"<i>\"{transcript}\"</i>\n\n"
            f"<i>Transcribed via Gnani Prisma v3.0{timing_str}</i>"
        )
        state["voice_bytes"] = None

    status = state.get("status")
    engine = state.get("llm_engine") or "Neurons Nano"
    if status == "AWAITING_CLARIFICATION":
        clarify_audio = state.get("clarification_audio_path")
        async with ChatActionSender.upload_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=clarify_audio,
                caption=f"<b>Voice Clarification ({engine}):</b> Please listen to the details needed.",
            )
        prompt = state.get("clarification_prompt", "Please provide missing order or name details.")
        if state.get("pending_confirmation_field"):
            kb = get_slot_confirmation_keyboard(state["pending_confirmation_field"])
            await message.answer(prompt, reply_markup=kb)
        else:
            await message.answer(prompt)

    elif status == "AWAITING_CONFIRMATION":
        assessment_audio = state.get("assessment_audio_path")
        async with ChatActionSender.upload_voice(chat_id=chat_id, bot=bot, initial_sleep=0.0, interval=4.0):
            await send_voice_with_fallback(
                bot=bot,
                chat_id=chat_id,
                audio_path=assessment_audio,
                caption="<b>Dispute Assessment Walkthrough:</b> Statutory claim summary.",
            )
        card = format_assessment_card(state)
        await message.answer(card, reply_markup=get_confirmation_keyboard())

    elif status == "GENERATED":
        await message.answer("Dossier generated.")

    # Persist updated turn state to SQLite
    user_id = state.get("telegram_user_id") or (str(message.from_user.id) if message.from_user else None)
    if user_id:
        await save_user_state(user_id, state)
