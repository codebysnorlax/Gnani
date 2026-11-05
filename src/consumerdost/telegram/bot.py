import io
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    TelegramObject,
    FSInputFile,
)
from aiogram.client.default import DefaultBotProperties

from consumerdost.config import settings
from consumerdost.database.engine import AsyncSessionLocal, init_db
from consumerdost.database.repository import DisputeRepository
from consumerdost.agent.state import ConsumerDostState
from consumerdost.agent.graph import get_compiled_graph
from consumerdost.agent.nodes import node_bundle, node_tts
from consumerdost.telegram.keyboards import (
    get_welcome_keyboard,
    get_confirmation_keyboard,
    get_dossier_action_keyboard,
)
from consumerdost.telegram.formatters import (
    format_welcome_message,
    format_assessment_card,
    format_cover_email,
)

logger = logging.getLogger(__name__)

# Active session cache per user: user_id -> ConsumerDostState
user_sessions: dict[str, ConsumerDostState] = {}


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


def get_user_state(user_id: str, chat_id: str) -> ConsumerDostState:
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
            await repo.get_or_create_user(user_id, chat_id)

        # Reset draft
        user_sessions[user_id] = {
            "telegram_user_id": user_id,
            "chat_id": chat_id,
            "thread_id": f"thread_{user_id}",
            "preferred_language": "hi-IN",
            "status": "DRAFT",
        }
        await message.answer(
            format_welcome_message(),
            reply_markup=get_welcome_keyboard(),
        )

    @dp.message(Command("newdispute"))
    @dp.message(Command("cancel"))
    async def cmd_new_dispute(message: Message):
        user_id = str(message.from_user.id)
        user_sessions[user_id] = {
            "telegram_user_id": user_id,
            "chat_id": str(message.chat.id),
            "thread_id": f"thread_{user_id}",
            "preferred_language": "hi-IN",
            "status": "DRAFT",
        }
        await message.answer(
            "🔄 Previous session cleared. Please speak or type your consumer dispute to begin."
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

        lines = ["📚 <b>Your Past Consumer Disputes:</b>\n"]
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

        user_sessions.pop(user_id, None)
        await message.answer(
            f"🗑️ <b>Data Deleted:</b> {deleted} dispute records and personal data have been completely purged from SQLite."
        )

    # 2. Callback Query Handlers
    @dp.callback_query(F.data.startswith("demo:"))
    async def handle_demo_callbacks(callback: CallbackQuery):
        demo_type = callback.data.split(":")[1]
        user_id = str(callback.from_user.id)
        state = get_user_state(user_id, str(callback.message.chat.id))

        if demo_type == "flipkart":
            demo_text = (
                "Bhaiya maine Flipkart se 14,999 ka phone 25 October ko mangaya tha. "
                "Order ID OD3091823901. Box khola toh screen tooti hui thi. "
                "Mera naam Rohan Sharma hai aur email rohan@example.com."
            )
        elif demo_type == "upi":
            demo_text = (
                "Maine kal ₹1,200 ka electricity bill pay kiya UPI se PhonePe par. "
                "Paisa bank se cut gaya par recharge fail ho gaya. UTR: 123456789012. "
                "Mera naam Sunita Devi hai aur mobile 9876543210."
            )
        else:
            demo_text = (
                "Indigo flight 6E-204 cancelled on 2026-11-01 without notice. "
                "Ticket amount was Rs 6,500. PNR 98765432. Return denied. "
                "My name is Vikram Seth (vikram@example.com)."
            )

        state["raw_input_text"] = demo_text
        await callback.message.answer(f"<i>Processing sample grievance:</i>\n\"{demo_text}\"")
        await process_workflow_turn(bot, callback.message, state)
        await callback.answer()

    @dp.callback_query(F.data == "action:generate_bundle")
    async def handle_generate_bundle(callback: CallbackQuery):
        user_id = str(callback.from_user.id)
        state = get_user_state(user_id, str(callback.message.chat.id))

        await callback.message.answer("⚙️ <i>Generating your complete Tri-Fold Escalation Dossier...</i>")

        # 1. Run bundle generator
        bundle_res = await node_bundle(state)
        state.update(bundle_res)

        # 2. Run TTS
        tts_res = await node_tts(state)
        state.update(tts_res)

        # 3. Save to database
        brand_info = state.get("brand_resolved") or {}
        case_ref = state.get("case_reference_id") or "CD-2026-0001"
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
                caption=f"📄 <b>Official Legal Notice:</b> {case_ref}\nServe this directly to the brand's statutory Nodal Officer.",
            )
            await callback.message.answer(format_cover_email(state))

        # 5. Deliver Document 2: NCH 1915 WhatsApp Dossier Block
        nch_text = state.get("nch_dossier_text")
        if nch_text:
            await callback.message.answer(
                f"🏛️ <b>Document 2: National Consumer Helpline (NCH 1915) Dossier</b>\n\n"
                f"<pre>{nch_text}</pre>"
            )

        # 6. Deliver Document 3: Public Social Escalation Post (X)
        twitter_text = state.get("twitter_draft_text")
        if twitter_text:
            await callback.message.answer(
                f"🐦 <b>Document 3: Public Social Escalation Post (<280 chars)</b>\n\n"
                f"<code>{twitter_text}</code>"
            )

        # 7. Deliver Document 4: Gnani Timbre TTS Voice Note
        tts_audio = state.get("tts_audio_path")
        if tts_audio and Path(tts_audio).exists():
            audio_file = FSInputFile(tts_audio, filename=f"Voice_Summary_{case_ref}.wav")
            await callback.message.answer_voice(
                voice=audio_file,
                caption="🎙️ <b>Gnani Voice Guide:</b> 15-second action walkthrough in your preferred language.",
            )

        # 8. Interactive Action Buttons
        wa_url = state.get("nch_whatsapp_url", "https://wa.me/918860005372")
        tw_url = state.get("twitter_intent_url", "https://twitter.com")
        await callback.message.answer(
            "✅ <b>Tri-Fold Escalation Dossier Complete!</b>\n"
            "Use the buttons below to open NCH WhatsApp or post your public escalation post on X immediately:",
            reply_markup=get_dossier_action_keyboard(wa_url, tw_url),
        )
        await callback.answer()

    @dp.callback_query(F.data == "action:edit_details")
    async def handle_edit_details(callback: CallbackQuery):
        await callback.message.answer(
            "✏️ To update your details, please type your correction (for example:\n"
            "• <i>Change amount to 15499</i>\n"
            "• <i>My Order ID is OD99887766</i>\n"
            "• <i>Change date to 26 October</i>)"
        )
        await callback.answer()

    @dp.callback_query(F.data == "action:cancel")
    async def handle_cancel(callback: CallbackQuery):
        user_id = str(callback.from_user.id)
        user_sessions.pop(user_id, None)
        await callback.message.answer("❌ Dispute draft cancelled.")
        await callback.answer()

    # 3. Message Handlers (Voice and Text)
    @dp.message(F.voice)
    async def handle_voice_message(message: Message):
        # 60 second duration cap
        if message.voice.duration > 60:
            await message.answer("⚠️ Voice note is over 60 seconds. Please send a shorter voice note or type your complaint.")
            return

        user_id = str(message.from_user.id)
        state = get_user_state(user_id, str(message.chat.id))

        await message.answer("🎙️ <i>Listening and transcribing with Gnani Prisma v3.0 STT...</i>")

        # Download voice file
        file_obj = io.BytesIO()
        await bot.download(message.voice.file_id, destination=file_obj)
        state["voice_bytes"] = file_obj.getvalue()
        state["raw_input_text"] = None

        await process_workflow_turn(bot, message, state)

    @dp.message(F.text)
    async def handle_text_message(message: Message):
        user_id = str(message.from_user.id)
        state = get_user_state(user_id, str(message.chat.id))

        state["raw_input_text"] = message.text
        state["voice_bytes"] = None

        await process_workflow_turn(bot, message, state)

    return bot, dp


async def process_workflow_turn(bot: Bot, message: Message, state: ConsumerDostState) -> None:
    """Run LangGraph pipeline turn and reply with clarification or assessment card."""
    graph = await get_compiled_graph()
    result = await graph.ainvoke(state)
    state.update(result)

    status = state.get("status")
    if status == "AWAITING_CLARIFICATION":
        prompt = state.get("clarification_prompt", "Please provide missing order or name details.")
        await message.answer(f"ℹ️ {prompt}")
    elif status == "AWAITING_CONFIRMATION":
        card = format_assessment_card(state)
        await message.answer(card, reply_markup=get_confirmation_keyboard())
    elif status == "GENERATED":
        await message.answer("Dossier generated.")
