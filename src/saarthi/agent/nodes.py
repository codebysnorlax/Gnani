import logging
import re
from datetime import date
from pathlib import Path
from typing import Any
import inspect

from saarthi.config import settings
from saarthi.agent.state import ConsumerDostState
from saarthi.speech.gnani_stt import stt_service, detect_indic_script_language
from saarthi.speech.gnani_tts import tts_service, normalize_language_code
from saarthi.agent.voice_prompts import VoicePromptComposer
from saarthi.agent.response_composer import ResponseComposer
from saarthi.security.pii_scrubber import scrub_sensitive_pii
from saarthi.agent.llm_router import llm_router
from saarthi.agent.regex_fallback import parse_date_from_text
from saarthi.domain.brands import resolve_brand
from saarthi.domain.statutes import get_statute_entry
from saarthi.domain.calculator import calculate_claim, format_inr
from saarthi.documents.pdf_generator import generate_legal_notice_pdf
from saarthi.documents.nch_formatter import format_nch_dossier
from saarthi.documents.social_formatter import format_twitter_escalation

logger = logging.getLogger(__name__)


async def _notify_progress(cb: Any, text: str) -> None:
    if not cb:
        return
    try:
        if inspect.iscoroutinefunction(cb):
            await cb(text)
        elif callable(cb):
            res = cb(text)
            if inspect.isawaitable(res):
                await res
    except Exception:
        pass


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
        "preferred_voice_character": state.get("preferred_voice_character") or "Shivani",
        "is_explicit_language": state.get("is_explicit_language", False),
        "detected_script_language": detected_lang,
    }
    if stt_service.last_latency_ms is not None:
        res["stt_latency_ms"] = stt_service.last_latency_ms
    return res


async def node_scrub(state: ConsumerDostState) -> dict:
    """Deterministically scrub payment card numbers, secrets, and govt IDs."""
    raw = state.get("raw_input_text") or ""
    target_field = state.get("clarification_target_field")
    sanitized = scrub_sensitive_pii(raw, target_field=target_field)
    return {"sanitized_transcript": sanitized}


async def node_parse(state: ConsumerDostState) -> dict:
    """Extract structured dispute entities via cascading LLM router."""
    sanitized = state.get("sanitized_transcript") or state.get("raw_input_text") or ""
    progress_cb = state.get("progress_callback")
    neurons_model = state.get("neurons_model")
    draft, tier = await llm_router.extract_dispute_facts(
        sanitized,
        progress_callback=progress_cb,
        preferred_model=neurons_model,
    )

    updates = {
        "llm_engine": getattr(llm_router, "last_engine", "Neurons Nano"),
    }
    if draft.brand_raw and not state.get("brand_raw"):
        updates["brand_raw"] = draft.brand_raw
    if draft.amount_paid_inr and not state.get("amount_paid_inr"):
        updates["amount_paid_inr"] = draft.amount_paid_inr
    if draft.incident_date and not state.get("incident_date"):
        updates["incident_date"] = draft.incident_date
    if draft.order_id and not state.get("order_id"):
        updates["order_id"] = draft.order_id
    if draft.complainant_full_name and not state.get("complainant_full_name"):
        clean_name = re.sub(r"\s+(?:hai|tha)$", "", draft.complainant_full_name, flags=re.IGNORECASE).strip()
        updates["complainant_full_name"] = clean_name
    if draft.complainant_contact and not state.get("complainant_contact"):
        updates["complainant_contact"] = draft.complainant_contact
    if draft.category:
        updates["dispute_category"] = draft.category
    if draft.issue_type:
        updates["issue_type"] = draft.issue_type
    if draft.incident_summary:
        updates["dispute_narrative_en"] = draft.incident_summary

    # Contextual short-answer disambiguation for pending clarification field
    target_field = state.get("clarification_target_field")
    cleaned_input = sanitized.strip()

    if target_field == "full_name" and not updates.get("complainant_full_name") and not state.get("complainant_full_name"):
        name_candidate = re.sub(
            r"^(?:no,?\s*|nahi,?\s*)?(?:my\s+name\s+is|i\s+am|naam|mera\s+naam)\s*(?:is|hai|tha)?\s*",
            "",
            cleaned_input,
            flags=re.IGNORECASE,
        ).strip(". ")
        name_candidate = re.sub(r"\s+(?:hai|tha)$", "", name_candidate, flags=re.IGNORECASE).strip(". ")
        if name_candidate and len(name_candidate.split()) <= 5 and not re.search(r"\d", name_candidate):
            updates["complainant_full_name"] = name_candidate.title()

    elif target_field == "amount" and not state.get("amount_paid_inr"):
        # If user directly provided a number or currency (e.g. "30000", "₹30,000", "30000 rs")
        amt_match = re.search(
            r"^(?:no,?\s*|nahi,?\s*)?(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+)\s*(?:₹|rs\.?|inr|rupees)?$",
            cleaned_input,
            re.IGNORECASE,
        )
        if amt_match:
            try:
                val = float(amt_match.group(1).replace(",", ""))
                if val > 0:
                    updates["amount_paid_inr"] = val
            except ValueError:
                pass
        elif not updates.get("amount_paid_inr"):
            amt_match2 = re.search(
                r"(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?|[0-9]+)\s*(?:₹|rs\.?|inr|rupees)?",
                cleaned_input,
                re.IGNORECASE,
            )
            if amt_match2:
                try:
                    val = float(amt_match2.group(1).replace(",", ""))
                    if val > 0:
                        updates["amount_paid_inr"] = val
                except ValueError:
                    pass

    elif target_field == "order_id" and not updates.get("order_id") and not state.get("order_id"):
        from saarthi.agent.regex_fallback import EXPLICIT_ORDER_PATTERN
        exp_m = EXPLICIT_ORDER_PATTERN.search(cleaned_input)
        if exp_m:
            updates["order_id"] = exp_m.group(1).strip().upper()
        else:
            order_candidate = re.sub(
                r"^(?:no,?\s*|nahi,?\s*)?(?:my\s+|mera\s+|meri\s+|ye\s+)?(?:order|id|ref|pnr|utr|txn|transaction)(?:\s*(?:id|no|number|code))?\s*(?:is|hai|tha)?\s*[:#-]?\s*",
                "",
                cleaned_input,
                flags=re.IGNORECASE,
            ).strip(". ")
            order_candidate = re.sub(r"\s+(?:hai|tha)$", "", order_candidate, flags=re.IGNORECASE).strip(". ")
            if order_candidate and len(order_candidate.split()) == 1 and len(order_candidate) >= 4:
                updates["order_id"] = order_candidate.upper()

    elif target_field == "incident_date" and not updates.get("incident_date") and not state.get("incident_date"):
        clean_date_input = re.sub(r"^(?:no,?\s*|nahi,?\s*)?", "", cleaned_input, flags=re.IGNORECASE).strip()
        parsed_date = parse_date_from_text(clean_date_input)
        if parsed_date:
            updates["incident_date"] = parsed_date

    elif target_field == "brand" and not updates.get("brand_raw") and not state.get("brand_raw"):
        brand_candidate = re.sub(
            r"^(?:no,?\s*|nahi,?\s*)?(?:company|brand|vendor|dukandar|seller|dukaan|for|from)?\s*(?:name|ka\s+naam)?\s*(?:is|hai|tha)?\s*[:#-]?\s*",
            "",
            cleaned_input,
            flags=re.IGNORECASE,
        ).strip(". ")
        brand_candidate = re.sub(r"\s+(?:hai|tha)$", "", brand_candidate, flags=re.IGNORECASE).strip(". ")
        if brand_candidate and len(brand_candidate.split()) <= 5:
            updates["brand_raw"] = brand_candidate.title()

    # Check if a specific field was requested during fallback (Tier 3) mode
    if target_field and tier == 3:
        candidate = None
        if target_field == "incident_date" and updates.get("incident_date"):
            candidate = updates.pop("incident_date")
        elif target_field == "order_id" and updates.get("order_id"):
            candidate = updates.pop("order_id")
        elif target_field == "amount" and updates.get("amount_paid_inr"):
            candidate = updates.pop("amount_paid_inr")
        elif target_field == "brand" and updates.get("brand_raw"):
            candidate = updates.pop("brand_raw")
        elif target_field == "full_name" and updates.get("complainant_full_name"):
            candidate = updates.pop("complainant_full_name")

        if candidate is not None:
            updates["pending_confirmation_field"] = target_field
            updates["pending_confirmation_value"] = candidate

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

CLARIFICATION_PRIORITY = ["brand", "amount", "order_id", "incident_date", "full_name"]


async def node_clarify(state: ConsumerDostState) -> dict:
    """Build targeted dynamic context-aware single-field clarification prompt and voice note."""
    missing = state.get("missing_fields", [])
    if not missing and not state.get("pending_confirmation_field"):
        return {"clarification_prompt": None, "clarification_audio_path": None}

    lang = state.get("preferred_language", "hi-IN")
    detected = state.get("detected_script_language")
    if detected == "en-IN" and not state.get("is_explicit_language"):
        lang = "en-IN"

    voice_char = state.get("preferred_voice_character") or "Shivani"
    progress_cb = state.get("progress_callback")

    # If user provided a slot value in fallback mode, ask for explicit confirmation
    pending_field = state.get("pending_confirmation_field")
    pending_val = state.get("pending_confirmation_value")
    if pending_field and pending_val is not None:
        val_display = format_inr(float(pending_val)) if pending_field == "amount" else str(pending_val)
        is_hi = lang.startswith("hi") or lang == "hinglish"
        if is_hi:
            prompt_text = (
                f"आपने यह विवरण दिया है:\n<b>{val_display}</b>\n\n"
                "कृपया पुष्टि करें कि क्या यह सही है।"
            )
            spoken_script = f"Aapne yeh vivaran diya hai: {val_display}. <pauses> Kripya confirm karein."
        else:
            prompt_text = (
                f"You provided this:\n<b>{val_display}</b>\n\n"
                "Please confirm if this is correct."
            )
            spoken_script = f"You provided this: {val_display}. <pauses> Please confirm if this is correct."

        user_id = state.get("telegram_user_id", "user")
        thread_id = state.get("thread_id", "thread")
        audio_path = settings.data_dir / "artifacts" / f"Confirm_{user_id}_{pending_field}.wav"

        await _notify_progress(progress_cb, "Cooking voice guidance...")
        audio_res = await tts_service.synthesize_speech(
            text=spoken_script,
            output_path=audio_path,
            language=lang,
            voice=voice_char,
            model="timbre-v3.0",
        )

        return {
            "clarification_prompt": prompt_text,
            "clarification_audio_path": str(audio_res) if audio_res else None,
            "status": "AWAITING_CLARIFICATION",
            "clarification_target_field": pending_field,
            "pending_confirmation_field": pending_field,
            "pending_confirmation_value": pending_val,
            "missing_fields": missing,
            "preferred_voice_character": voice_char,
            "is_explicit_language": state.get("is_explicit_language"),
            "llm_engine": "Standard Engine",
        }

    target_field = None
    for f in CLARIFICATION_PRIORITY:
        if f in missing:
            target_field = f
            break
    if not target_field and missing:
        target_field = missing[0]

    prev_target = state.get("clarification_target_field")
    latest_input = state.get("raw_input_text")
    is_invalid_retry = bool(
        prev_target
        and prev_target == target_field
        and latest_input
        and latest_input.strip()
    )

    neurons_model = state.get("neurons_model")
    composed = await ResponseComposer.compose_clarification(
        known_facts=dict(state),
        target_field=target_field,
        language=lang,
        latest_user_text=latest_input,
        voice_character=voice_char,
        progress_callback=progress_cb,
        preferred_model=neurons_model,
        is_invalid_retry=is_invalid_retry,
    )
    prompt_text = composed.visible_text
    spoken_script = composed.spoken_text

    user_id = state.get("telegram_user_id", "user")
    thread_id = state.get("thread_id", "thread")
    audio_path = settings.data_dir / "artifacts" / f"Clarification_{user_id}_{thread_id}.wav"

    await _notify_progress(progress_cb, "Cooking voice guidance...")
    audio_res = await tts_service.synthesize_speech(
        text=spoken_script,
        output_path=audio_path,
        language=lang,
        voice=voice_char,
        model="timbre-v3.0",
    )

    return {
        "clarification_prompt": prompt_text,
        "clarification_audio_path": str(audio_res) if audio_res else None,
        "status": "AWAITING_CLARIFICATION",
        "clarification_target_field": target_field,
        "missing_fields": missing,
        "preferred_voice_character": voice_char,
        "is_explicit_language": state.get("is_explicit_language"),
        "llm_engine": composed.engine,
    }


async def node_resolve(state: ConsumerDostState) -> dict:
    """Resolve brand against directory, map statutes, and calculate paise claim."""
    progress_cb = state.get("progress_callback")
    await _notify_progress(progress_cb, "Searching consumer statutes & calculating legal claim...")

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
    voice_char = state.get("preferred_voice_character") or "Shivani"
    total_rupees = claim.total_demanded_paise / 100.0
    assessment_script = VoicePromptComposer.compose_assessment(total_rupees, language=lang)
    audio_path = settings.data_dir / "artifacts" / f"Assessment_{case_ref}.wav"
    await _notify_progress(progress_cb, "Cooking assessment audio...")
    assessment_audio = await tts_service.synthesize_speech(
        text=assessment_script,
        output_path=audio_path,
        language=lang,
        voice=voice_char,
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
    progress_cb = state.get("progress_callback")
    await _notify_progress(progress_cb, "Writing legal notice & escalation dossier...")
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
