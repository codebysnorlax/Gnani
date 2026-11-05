import logging
from datetime import date
from pathlib import Path

from consumerdost.config import settings
from consumerdost.agent.state import ConsumerDostState
from consumerdost.speech.gnani_stt import stt_service
from consumerdost.speech.gnani_tts import tts_service
from consumerdost.security.pii_scrubber import scrub_sensitive_pii
from consumerdost.agent.llm_router import llm_router
from consumerdost.domain.brands import resolve_brand
from consumerdost.domain.statutes import get_statute_entry
from consumerdost.domain.calculator import calculate_claim, format_inr
from consumerdost.documents.pdf_generator import generate_legal_notice_pdf
from consumerdost.documents.nch_formatter import format_nch_dossier
from consumerdost.documents.social_formatter import format_twitter_escalation

logger = logging.getLogger(__name__)


async def node_ingest(state: ConsumerDostState) -> dict:
    """Ingest voice or text input and transcribe voice using Gnani Prisma v3.0 STT."""
    voice_bytes = state.get("voice_bytes")
    transcript = state.get("raw_input_text") or ""

    if voice_bytes:
        lang = state.get("preferred_language", "hi-IN")
        text, is_fallback = await stt_service.transcribe_audio(
            audio_source=voice_bytes,
            filename="voice.ogg",
            language_code="hi-IN" if lang.startswith("hi") else "en-IN",
        )
        if text:
            transcript = text

    return {"raw_input_text": transcript}


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


async def node_clarify(state: ConsumerDostState) -> dict:
    """Build single targeted clarification prompt for missing fields."""
    missing = state.get("missing_fields", [])
    if not missing:
        return {"clarification_prompt": None}

    field_prompts = []
    if "order_id" in missing:
        field_prompts.append("• Exact Order ID, PNR, or 12-digit UPI UTR")
    if "full_name" in missing:
        field_prompts.append("• Your Full Legal Name (as Sender on the Legal Notice)")
    if "brand" in missing:
        field_prompts.append("• The Company or Brand name")
    if "amount" in missing:
        field_prompts.append("• The exact amount paid in INR (e.g. ₹1,499)")
    if "incident_date" in missing:
        field_prompts.append("• Approximate transaction date (e.g. 25 Oct 2026)")

    prompt_text = (
        "Voice grievance recorded. To generate your official Legal Demand Notice, "
        "please type or paste the following details:\n\n"
        + "\n".join(field_prompts)
    )
    return {
        "clarification_prompt": prompt_text,
        "status": "AWAITING_CLARIFICATION",
    }


async def node_resolve(state: ConsumerDostState) -> dict:
    """Resolve brand against directory, map statutes, and calculate paise claim."""
    brand_raw = state.get("brand_raw") or "Generic Vendor"
    brand_info = resolve_brand(brand_raw)
    if not brand_info:
        # Fallback corporate info
        brand_info = {
            "canonical_name": brand_raw.upper(),
            "aliases": [brand_raw.lower()],
            "corporate_name": brand_raw,
            "registered_address": "Registered Office, India",
            "nodal_officer_name": "Nodal Grievance Officer",
            "nodal_email": "grievance@" + brand_raw.lower().replace(" ", "") + ".com",
            "twitter_handle": "@" + brand_raw.replace(" ", ""),
            "category": state.get("dispute_category", "E_COMMERCE"),
        }

    issue_type = state.get("issue_type", "ECOMMERCE_REFUND_DELAY_OR_DENIAL")
    statute_entry = get_statute_entry(issue_type)

    amt = state.get("amount_paid_inr") or 0.0
    inc_date = state.get("incident_date") or date.today().isoformat()
    claim = calculate_claim(amt, inc_date, issue_type=issue_type)

    case_ref = state.get("case_reference_id")
    if not case_ref:
        import uuid
        case_ref = f"CD-{date.today().year}-{uuid.uuid4().hex[:4].upper()}"

    legal_clauses = statute_entry.cpa_sections + statute_entry.sectoral_rules

    return {
        "brand_resolved": brand_info,
        "case_reference_id": case_ref,
        "legal_clauses": legal_clauses,
        "principal_paise": claim.principal_paise,
        "calculated_interest_paise": claim.interest_paise,
        "statutory_penalty_paise": claim.statutory_penalty_paise,
        "damages_claimed_paise": claim.damages_paise,
        "total_claim_paise": claim.total_demanded_paise,
        "status": "AWAITING_CONFIRMATION",
    }


async def node_bundle(state: ConsumerDostState) -> dict:
    """Generate the Tri-Fold Escalation Dossier: PDF Notice, NCH Dossier, X Draft."""
    case_ref = state.get("case_reference_id") or "CD-2026-0001"
    brand_info = state.get("brand_resolved") or {}
    claim = calculate_claim(
        state.get("amount_paid_inr", 0.0),
        state.get("incident_date", date.today().isoformat()),
        issue_type=state.get("issue_type"),
    )
    statute_entry = get_statute_entry(state.get("issue_type"))

    # 1. Generate PDF
    artifacts_dir = settings.data_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = artifacts_dir / f"Legal_Notice_{case_ref}.pdf"

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
        is_demo_mode=settings.demo_mode,
    )

    # 2. Generate NCH Dossier
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

    # 3. Generate X Draft
    social_res = format_twitter_escalation(
        brand_handle=brand_info.get("twitter_handle"),
        order_id=state.get("order_id") or "N/A",
        amount_inr=state.get("amount_paid_inr", 0.0),
        issue_snippet=state.get("issue_type", "").replace("_", " ").title(),
    )

    return {
        "pdf_file_path": str(pdf_path),
        "nch_dossier_text": nch_res["dossier_text"],
        "nch_whatsapp_url": nch_res["whatsapp_url"],
        "twitter_draft_text": social_res["tweet_text"],
        "twitter_intent_url": social_res["intent_url"],
        "status": "GENERATED",
    }


async def node_tts(state: ConsumerDostState) -> dict:
    """Generate closing audio note using Gnani Timbre TTS."""
    case_ref = state.get("case_reference_id") or "CD-0001"
    audio_path = settings.data_dir / "artifacts" / f"Audio_Summary_{case_ref}.wav"
    lang = state.get("preferred_language", "hi-IN")

    result_path = await tts_service.synthesize_action_summary(
        output_path=audio_path,
        language=lang,
    )
    return {"tts_audio_path": str(result_path) if result_path else None}
