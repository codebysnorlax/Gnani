from typing import TypedDict, Any
from saarthi.domain.brands import BrandInfo


class SaarthiState(TypedDict, total=False):
    telegram_user_id: str
    chat_id: str
    thread_id: str
    preferred_language: str  # 'hi-IN', 'hinglish', or 'en-IN'
    raw_input_text: str | None
    voice_file_id: str | None
    voice_bytes: bytes | None
    sanitized_transcript: str | None
    complainant_full_name: str | None
    complainant_contact: str | None
    brand_raw: str | None
    brand_resolved: BrandInfo | None
    order_id: str | None
    incident_date: str | None  # YYYY-MM-DD
    amount_paid_inr: float | None
    dispute_category: str | None
    issue_type: str | None
    dispute_narrative_en: str | None
    communication_summary: str | None
    missing_fields: list[str]
    clarification_prompt: str | None
    legal_clauses: list[str]
    principal_paise: int
    calculated_interest_paise: int
    statutory_penalty_paise: int
    damages_claimed_paise: int
    total_claim_paise: int
    case_reference_id: str | None
    pdf_file_path: str | None
    nch_dossier_text: str | None
    nch_whatsapp_url: str | None
    twitter_draft_text: str | None
    twitter_intent_url: str | None
    tts_audio_path: str | None
    clarification_audio_path: str | None
    assessment_audio_path: str | None
    welcome_audio_path: str | None
    status: str
    error_message: str | None
    demo_type: str | None
    is_demo: bool | None
    stt_latency_ms: int | None
    tts_latency_ms: int | None
    clarification_target_field: str | None
    bundle_errors: list[str] | None


# Backward-compatible alias
ConsumerDostState = SaarthiState


