import io
import re
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

from saarthi.config import settings
from saarthi.database.engine import AsyncSessionLocal, init_db
from saarthi.database.repository import DisputeRepository
from saarthi.agent.state import ConsumerDostState
from saarthi.agent.graph import get_compiled_graph, run_atomic_generation
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


async def send_voice_with_fallback(
    bot: Bot,
    chat_id: int | str,
    audio_path: str | Path | None,
    caption: str | None = None,
) -> bool:
    """Send voice message to chat if file exists, logging warning on failure."""
    if audio_path and Path(audio_path).exists():
        try:
            voice_file = FSInputFile(str(audio_path))
            await bot.send_voice(chat_id=chat_id, voice=voice_file, caption=caption)
            return True
        except Exception as e:
            logger.warning(f"Could not send voice note to {chat_id}: {e}")
    return False


async def setup_bot_commands(bot: Bot) -> None:
    """Register menu commands with Telegram so they appear in the input box menu."""
    commands = [
        BotCommand(command="start", description="Start SAARTHI assistance"),
        BotCommand(command="lang", description="Choose language / भाषा चुनें"),
        BotCommand(command="gender", description="Choose voice & gender / आवाज़ और लिंग चुनें"),
        BotCommand(command="newdispute", description="Start fresh dispute session"),
        BotCommand(command="mycases", description="View past dispute cases"),
        BotCommand(command="privacy", description="Purge personal data"),
    ]
    try:
        await bot.set_my_commands(commands)
        logger.info("Registered Telegram input box menu commands: /lang, /gender, etc.")
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


def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
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

        # 2. Companion text and clean input area (removes persistent custom keyboards)
        await message.answer(
            format_welcome_message(),
            reply_markup=ReplyKeyboardRemove(),
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
        await callback.message.answer(
            "Previous case cleared. Please speak or type your consumer dispute to begin:",
            reply_markup=ReplyKeyboardRemove(),
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
        await message.answer(
            "Previous session cleared. Please speak or type your consumer dispute to begin.",
            reply_markup=ReplyKeyboardRemove(),
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
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)

        # 1. Run atomic bundle and TTS generation via LangGraph
        try:
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

        state["raw_input_text"] = message.text
        state["voice_bytes"] = None

        await process_workflow_turn(bot, message, state)

    return bot, dp


def is_conversational_greeting_or_help(text: str) -> bool:
    """Detect if user input is an introductory greeting, capability query, or chit-chat."""
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

    return False


async def handle_conversational_inquiry(bot: Bot, message: Message, state: ConsumerDostState) -> None:
    """Respond dynamically to greetings and capability questions in chosen voice and user's language."""
    chat_id = str(message.chat.id)
    raw_text = state.get("raw_input_text") or getattr(message, "text", None) or ""
    voice_char = state.get("preferred_voice_character") or "Shivani"
    gender = get_voice_gender(voice_char)

    detected = detect_indic_script_language(raw_text)
    is_english = (detected == "en-IN") or bool(re.search(r"^[a-zA-Z0-9\s\.,\?!'-]+$", raw_text))

    if is_english:
        lang = "en-IN"
        visible_text = (
            "<b>Hello! I am SAARTHI (pronounced saar-thee)</b>\n"
            "<i>Your Voice-First AI Consumer Rights & Dispute Guide</i>\n\n"
            "I help consumers resolve unfair disputes with e-commerce platforms, airlines, banks, and service providers.\n\n"
            "<b>Here is how I can assist you:</b>\n"
            "• <b>Legal Claim Calculation:</b> Quantify refund amounts, statutory interest (6-18% p.a.), and legal damages under the Consumer Protection Act, 2019.\n"
            "• <b>Formal Legal Demand Notice (PDF):</b> Draft a lawyer-grade notice addressed to the company's Nodal Grievance Officer.\n"
            "• <b>National Consumer Helpline (NCH 1915):</b> Provide structured filing details ready for WhatsApp filing.\n"
            "• <b>Public Social Escalation:</b> Create a factual escalation draft for X (Twitter).\n"
            "• <b>Voice Guidance:</b> Provide clear spoken voice walkthroughs in your chosen voice.\n\n"
            "<b>To begin:</b> Tell me which company or brand you have an issue with, and what happened!"
        )
        spoken_text = (
            f"Hello! I am {voice_char} from SAARTHI, your consumer dispute assistant. <pauses> "
            "I convert consumer grievances into formal legal demand notices and helpline filings under the Consumer Protection Act. "
            "<slow> Please tell me which company or brand you have an issue with, and what happened."
        )
    else:
        lang = state.get("preferred_language") or "hi-IN"
        verb_help = "मदद करूँगी" if gender == "female" else "मदद करूंगा"
        verb_prepare = "तैयार करूँगी" if gender == "female" else "तैयार करूंगा"
        verb_can = "सकती हूँ" if gender == "female" else "सकता हूँ"
        visible_text = (
            f"<b>नमस्ते! मैं सारथी (SAARTHI) हूँ</b>\n"
            f"<i>आपका उपभोक्ता अधिकार और कानूनी शिकायत सहायक</i>\n\n"
            f"अगर किसी कंपनी (जैसे Flipkart, Amazon, एयरलाइंस या बैंक) ने आपका रिफंड अटकाया है या सेवा में कमी की है, तो मैं आपकी पूरी {verb_help}।\n\n"
            f"<b>मैं आपके लिए क्या कर {verb_can}:</b>\n"
            f"• <b>कानूनी दावे की गणना:</b> उपभोक्ता संरक्षण कानून के तहत ब्याज और हर्जाने की सटीक गणना।\n"
            f"• <b>लीगल नोटिस (PDF):</b> कंपनी के नोडल अधिकारी के लिए औपचारिक कानूनी मांग पत्र।\n"
            f"• <b>राष्ट्रीय उपभोक्ता हेल्पलाइन (NCH 1915):</b> व्हाट्सएप पर शिकायत दर्ज करने के लिए ड्राफ्ट टेक्स्ट।\n"
            f"• <b>सोशल मीडिया ड्राफ्ट:</b> X (Twitter) पर पोस्ट के लिए ड्राफ्ट।\n"
            f"• <b>ऑडियो मार्गदर्शन:</b> आपकी चुनी हुई आवाज़ ({voice_char}) में वॉइस गाइड।\n\n"
            f"<b>शुरुआत करने के लिए:</b> बस एक वॉइस नोट भेजें या लिखकर बताएं कि किस कंपनी या ब्रांड के साथ क्या समस्या हुई है।"
        )
        spoken_text = (
            f"Namaste! Main {voice_char} hoon, SAARTHI se. <pauses> "
            f"Consumer dispute sunkar main turant legal notice aur helpline filing {verb_prepare}. "
            f"<slow> Kripya batayein kis company ya brand ke saath kya samasya hui thi."
        )

    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
    cache_path = settings.data_dir / "cache" / f"help_intro_{lang}_{voice_char}.wav"
    audio_path = await tts_service.synthesize_speech(
        text=spoken_text,
        output_path=cache_path,
        language=lang,
        voice=voice_char,
        model="timbre-v3.0",
    )

    if audio_path and audio_path.exists():
        await send_voice_with_fallback(
            bot=bot,
            chat_id=chat_id,
            audio_path=audio_path,
            caption=f"<b>SAARTHI Overview:</b> Spoken by {voice_char}",
        )

    await message.answer(visible_text)
    state["status"] = "DRAFT"
    user_id = state.get("telegram_user_id") or (str(message.from_user.id) if getattr(message, "from_user", None) else "")
    if user_id:
        await save_user_state(user_id, state)


async def process_workflow_turn(bot: Bot, message: Message, state: ConsumerDostState) -> None:
    """Run LangGraph pipeline turn and reply with voice-first clarification or assessment card."""
    chat_id = str(message.chat.id)
    await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

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
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
        clarify_audio = state.get("clarification_audio_path")
        await send_voice_with_fallback(
            bot=bot,
            chat_id=chat_id,
            audio_path=clarify_audio,
            caption=f"<b>Voice Clarification ({engine}):</b> Please listen to the details needed.",
        )
        prompt = state.get("clarification_prompt", "Please provide missing order or name details.")
        await message.answer(prompt)

    elif status == "AWAITING_CONFIRMATION":
        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
        assessment_audio = state.get("assessment_audio_path")
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
