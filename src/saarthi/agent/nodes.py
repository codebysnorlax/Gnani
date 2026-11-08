import logging
from datetime import date
from pathlib import Path

from saarthi.config import settings
from saarthi.agent.state import ConsumerDostState
from saarthi.speech.gnani_stt import stt_service, detect_indic_script_language
from saarthi.speech.gnani_tts import tts_service, normalize_language_code
from saarthi.agent.voice_prompts import VoicePromptComposer
from saarthi.agent.response_composer import ResponseComposer
from saarthi.security.pii_scrubber import scrub_sensitive_pii
from saarthi.agent.llm_router import llm_router
from saarthi.domain.brands import resolve_brand
from saarthi.domain.statutes import get_statute_entry
from saarthi.domain.calculator import calculate_claim, format_inr
from saarthi.documents.pdf_generator import generate_legal_notice_pdf
from saarthi.documents.nch_formatter import format_nch_dossier
from saarthi.documents.social_formatter import format_twitter_escalation

logger = logging.getLogger(__name__)


async def node_ingest(state: ConsumerDostState) -> dict:
    """Ingest voice or text input and transcribe voice using Gnani Prisma v3.0 STT."""
    voice_bytes = state.get("voice_bytes")
    transcript = state.get("raw_input_text") or ""
    user_lang = state.get("preferred_language") or "hi-IN"

    detected_lang = None
    if voice_bytes:
        text, is_fallback = await stt_service.transcribe_audio(
            audio_source=voice_bytes,
            filename="voice.ogg",
            language_code=user_lang,
        )
        if text:
            transcript = text
            detected_lang = detect_indic_script_language(text)
    elif transcript:
        detected_lang = detect_indic_script_language(transcript)

    # Honor user's explicit language preference; detection is suggestion only
    res = {
        "raw_input_text": transcript,
        "preferred_language": user_lang,
        "detected_script_language": detected_lang,
    }
    if stt_service.last_latency_ms is not None:
        res["stt_latency_ms"] = stt_service.last_latency_ms
    return res


async def node_scrub(state: ConsumerDostState) -> dict:
    """Deterministically scrub payment card numbers, secrets, and govt IDs."""
    raw = state.get("raw_input_text") or ""
    sanitized = scrub_sensitive_pii(raw)
    return {"sanitized_transcript": sanitized}


async def node_parse(state: ConsumerDostState) -> dict:
    """Extract structured dispute entities via 4-tier LLM router."""
    sanitized = state.get("sanitized_transcript") or ""
    draft, tier = await llm_router.extract_dispute_facts(sanitized)

    updates = {}
    if draft.brand_raw and not state.get("brand_raw"):
        updates["brand_raw"] = draft.brand_raw
    if draft.amount_paid_inr and not state.get("amount_paid_inr"):
        updates["amount_paid_inr"] = draft.amount_paid_inr
    if draft.incident_date and not state.get("incident_date"):
        updates["incident_date"] = draft.incident_date
    if draft.order_id and not state.get("order_id"):
        updates["order_id"] = draft.order_id
    if draft.complainant_full_name and not state.get("complainant_full_name"):
        updates["complainant_full_name"] = draft.complainant_full_name
    if draft.complainant_contact and not state.get("complainant_contact"):
        updates["complainant_contact"] = draft.complainant_contact
    if draft.category:
        updates["dispute_category"] = draft.category
    if draft.issue_type:
        updates["issue_type"] = draft.issue_type
    if draft.incident_summary:
        updates["dispute_narrative_en"] = draft.incident_summary

    # Merge existing state with new updates to check missing fields
    current_brand = updates.get("brand_raw") or state.get("brand_raw")
    current_amount = updates.get("amount_paid_inr") or state.get("amount_paid_inr")
    current_date = updates.get("incident_date") or state.get("incident_date")
    current_order = updates.get("order_id") or state.get("order_id")
    current_name = updates.get("complainant_full_name") or state.get("complainant_full_name")

    missing = []
    if not current_brand:
        missing.append("brand")
    if current_amount is None or current_amount <= 0:
        missing.append("amount")
    if not current_date:
        missing.append("incident_date")
    if not current_order:
        missing.append("order_id")
    if not current_name:
        missing.append("full_name")

    updates["missing_fields"] = missing
    return updates

CLARIFICATION_PRIORITY = ["full_name", "order_id", "amount", "incident_date", "brand"]

FIELD_PROMPTS = {
    "full_name": (
        "🎙️ <b>One detail needed:</b>\n"
        "Please provide your <b>Full Legal Name</b> as Sender/Complainant on the legal notice."
    ),
    "order_id": (
        "🎙️ <b>One detail needed:</b>\n"
        "Please provide your <b>Order ID, booking PNR, or 12-digit UPI UTR</b>."
    ),
    "amount": (
        "🎙️ <b>One detail needed:</b>\n"
        "Please provide the <b>exact amount paid in INR</b> (e.g. ₹14,999)."
    ),
    "incident_date": (
        "🎙️ <b>One detail needed:</b>\n"
        "Please provide the <b>approximate transaction date</b> (e.g. 25 Oct 2026)."
    ),
    "brand": (
        "🎙️ <b>One detail needed:</b>\n"
        "Please provide the <b>Company or Brand name</b>."
    ),
}


async def node_clarify(state: ConsumerDostState) -> dict:
    """Build targeted dynamic context-aware single-field clarification prompt and voice note."""
    missing = state.get("missing_fields", [])
    if not missing:
        return {"clarification_prompt": None, "clarification_audio_path": None}

    # Select exactly one field by priority
    target_field = None
    for f in CLARIFICATION_PRIORITY:
        if f in missing:
            target_field = f
            break
    if not target_field:
        target_field = missing[0]

    lang = state.get("preferred_language", "hi-IN")
    composed = await ResponseComposer.compose_clarification(
        known_facts=dict(state),
        target_field=target_field,
        language=lang,
        latest_user_text=state.get("raw_input_text"),
    )
    prompt_text = composed.visible_text
    spoken_script = composed.spoken_text

    user_id = state.get("telegram_user_id", "user")
    thread_id = state.get("thread_id", "thread")
    audio_path = settings.data_dir / "artifacts" / f"Clarification_{user_id}_{thread_id}.wav"

    audio_res = await tts_service.synthesize_speech(
        text=spoken_script,
        output_path=audio_path,
        language=lang,
        persona="empathetic",
        model="timbre-v3.0",
    )

    return {
        "clarification_prompt": prompt_text,
        "clarification_audio_path": str(audio_res) if audio_res else None,
        "status": "AWAITING_CLARIFICATION",
        "clarification_target_field": target_field,
    }


async def node_resolve(state: ConsumerDostState) -> dict:
    """Resolve brand against directory, map statutes, and calculate paise claim."""
    brand_raw = state.get("brand_raw") or "Generic Vendor"
    brand_info = resolve_brand(
        brand_raw,
        fallback_if_unknown=True,
        custom_email=state.get("brand_email"),
        custom_address=state.get("brand_address"),
    )

    issue_type = state.get("issue_type", "ECOMMERCE_REFUND_DELAY_OR_DENIAL")
    statute_entry = get_statute_entry(issue_type)

    amt = state.get("amount_paid_inr") or 0.0
    inc_date = state.get("incident_date") or date.today().isoformat()
    claim = calculate_claim(amt, inc_date, issue_type=issue_type)

    case_ref = state.get("case_reference_id")
    if not case_ref:
        import uuid
        case_ref = f"SRTH-{date.today().year}-{uuid.uuid4().hex[:4].upper()}"

    legal_clauses = statute_entry.cpa_sections + statute_entry.sectoral_rules

    # Synthesize assessment walkthrough audio
    lang = state.get("preferred_language", "hi-IN")
    total_rupees = claim.total_demanded_paise / 100.0
    assessment_script = VoicePromptComposer.compose_assessment(total_rupees, language=lang)
    audio_path = settings.data_dir / "artifacts" / f"Assessment_{case_ref}.wav"
    assessment_audio = await tts_service.synthesize_speech(
        text=assessment_script,
        output_path=audio_path,
        language=lang,
        persona="empathetic",
        model="timbre-v3.0",
    )

    res = {
        "brand_resolved": brand_info,
        "case_reference_id": case_ref,
        "legal_clauses": legal_clauses,
        "principal_paise": claim.principal_paise,
        "calculated_interest_paise": claim.interest_paise,
        "statutory_penalty_paise": claim.statutory_penalty_paise,
        "damages_claimed_paise": claim.damages_paise,
        "total_claim_paise": claim.total_demanded_paise,
        "assessment_audio_path": str(assessment_audio) if assessment_audio else None,
        "status": "AWAITING_CONFIRMATION",
    }
    if tts_service.last_latency_ms is not None:
        res["tts_latency_ms"] = tts_service.last_latency_ms
    return res


async def node_bundle(state: ConsumerDostState) -> dict:
    """Generate the Tri-Fold Escalation Dossier: PDF Notice, NCH Dossier, X Draft."""
    if state.get("missing_fields"):
        raise ValueError(
            f"Cannot generate document bundle: missing required fields {state.get('missing_fields')}"
        )
    if state.get("status") == "AWAITING_CLARIFICATION":
        raise ValueError("Cannot generate document bundle: Case is awaiting clarification.")

    case_ref = state.get("case_reference_id") or "SRTH-2026-0001"
    brand_info = state.get("brand_resolved") or {}
    claim = calculate_claim(
        state.get("amount_paid_inr", 0.0),
        state.get("incident_date", date.today().isoformat()),
        issue_type=state.get("issue_type"),
    )
    statute_entry = get_statute_entry(state.get("issue_type"))

    bundle_errors: list[str] = []

    # 1. Generate PDF (Idempotent: if already generated and exists on disk, reuse)
    artifacts_dir = settings.data_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = artifacts_dir / f"Legal_Notice_{case_ref}.pdf"

    pdf_file_path = None
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        pdf_file_path = str(pdf_path)
    else:
        try:
            generate_legal_notice_pdf(
                output_path=pdf_path,
                case_reference_id=case_ref,
                notice_date=date.today(),
                complainant_name=state.get("complainant_full_name") or "Valued Consumer",
                complainant_contact=state.get("complainant_contact") or "Not Provided",
                brand_corporate_name=brand_info.get("corporate_name", "Respondent Brand"),
                registered_address=brand_info.get("registered_address", "India"),
                nodal_email=brand_info.get("nodal_email", "support@brand.com"),
                nodal_officer_name=brand_info.get("nodal_officer_name"),
                order_id=state.get("order_id") or "N/A",
                incident_date=state.get("incident_date") or date.today().isoformat(),
                narrative_facts=state.get("dispute_narrative_en") or "Dispute concerning consumer transaction.",
                statute_entry=statute_entry,
                claim=claim,
            )
            pdf_file_path = str(pdf_path)
        except Exception as e:
            logger.exception(f"PDF Notice generation failed for {case_ref}: {e}")
            bundle_errors.append("PDF_LEGAL_NOTICE")

    # 2. Generate NCH Dossier
    nch_dossier_text = None
    nch_whatsapp_url = None
    try:
        nch_res = format_nch_dossier(
            complainant_name=state.get("complainant_full_name") or "Consumer",
            complainant_contact=state.get("complainant_contact") or "N/A",
            brand_corporate_name=brand_info.get("corporate_name", "Brand"),
            order_id=state.get("order_id") or "N/A",
            incident_date=state.get("incident_date") or date.today().isoformat(),
            category=state.get("dispute_category") or "E_COMMERCE",
            claim=claim,
            facts_summary=state.get("dispute_narrative_en") or "",
        )
        nch_dossier_text = nch_res["dossier_text"]
        nch_whatsapp_url = nch_res["whatsapp_url"]
    except Exception as e:
        logger.exception(f"NCH Dossier generation failed for {case_ref}: {e}")
        bundle_errors.append("NCH_DOSSIER")

    # 3. Generate X Draft
    twitter_draft_text = None
    twitter_intent_url = None
    try:
        social_res = format_twitter_escalation(
            brand_handle=brand_info.get("twitter_handle"),
            order_id=state.get("order_id") or "N/A",
            amount_inr=state.get("amount_paid_inr", 0.0),
            issue_snippet=state.get("issue_type", "").replace("_", " ").title(),
        )
        twitter_draft_text = social_res["tweet_text"]
        twitter_intent_url = social_res["intent_url"]
    except Exception as e:
        logger.exception(f"Social escalation generation failed for {case_ref}: {e}")
        bundle_errors.append("TWITTER_DRAFT")

    status = "GENERATED" if not bundle_errors else "PARTIALLY_GENERATED"

    return {
        "pdf_file_path": pdf_file_path,
        "nch_dossier_text": nch_dossier_text,
        "nch_whatsapp_url": nch_whatsapp_url,
        "twitter_draft_text": twitter_draft_text,
        "twitter_intent_url": twitter_intent_url,
        "bundle_errors": bundle_errors,
        "status": status,
    }


async def node_tts(state: ConsumerDostState) -> dict:
    """Generate closing audio note using Gnani Timbre v3.0."""
    case_ref = state.get("case_reference_id") or "SRTH-0001"
    audio_path = settings.data_dir / "artifacts" / f"Audio_Summary_{case_ref}.wav"
    lang = state.get("preferred_language", "hi-IN")

    if audio_path.exists() and audio_path.stat().st_size > 0:
        return {"tts_audio_path": str(audio_path)}

    try:
        result_path = await tts_service.synthesize_action_summary(
            output_path=audio_path,
            language=lang,
        )
    except Exception as e:
        logger.exception(f"TTS audio synthesis failed for {case_ref}: {e}")
        result_path = None

    updates = {"tts_audio_path": str(result_path) if result_path else None}
    if not result_path:
        bundle_errors = list(state.get("bundle_errors") or [])
        bundle_errors.append("TTS_AUDIO")
        updates["bundle_errors"] = bundle_errors
        updates["status"] = "PARTIALLY_GENERATED"
    return updates
