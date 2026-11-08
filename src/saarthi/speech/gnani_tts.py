import logging
from pathlib import Path
from typing import Mapping

from gnani.tts import GnaniTTSClient, TIMBRE_V30_VOICES
from gnani.tts.exceptions import GnaniTTSError
from saarthi.config import settings
from saarthi.speech.tags import sanitize_tags_for_tts

logger = logging.getLogger(__name__)

SUPPORTED_INDIC_LANGUAGES: dict[str, str] = {
    "hi-IN": "Hindi",
    "en-IN": "English",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "pa-IN": "Punjabi",
    "bn-IN": "Bengali",
    "gu-IN": "Gujarati",
}

LANGUAGE_ALIAS_MAP: dict[str, str] = {
    "hindi": "hi-IN",
    "hi": "hi-IN",
    "english": "en-IN",
    "en": "en-IN",
    "hinglish": "hi-IN",
    "tamil": "ta-IN",
    "ta": "ta-IN",
    "telugu": "te-IN",
    "te": "te-IN",
    "kannada": "kn-IN",
    "kn": "kn-IN",
    "malayalam": "ml-IN",
    "ml": "ml-IN",
    "marathi": "mr-IN",
    "mr": "mr-IN",
    "punjabi": "pa-IN",
    "pa": "pa-IN",
    "bengali": "bn-IN",
    "bn": "bn-IN",
    "gujarati": "gu-IN",
    "gu": "gu-IN",
}

VOICE_PERSONAS: dict[str, str] = {
    "empathetic": "Shivani",
    "care": "Chetana",
    "reassuring": "Kalpana",
    "conversational": "Devansh",
    "professional": "Avinash",
    "authoritative": "Prakash",
    "energetic": "Shubham",
}

DEFAULT_MODEL = "timbre-v3.0"
DEFAULT_VOICE = "Shivani"


def normalize_language_code(lang: str | None) -> str:
    """Normalize language names or codes to official BCP-47 Indic format."""
    if not lang:
        return "hi-IN"
    clean = lang.strip().lower()
    if clean in LANGUAGE_ALIAS_MAP:
        return LANGUAGE_ALIAS_MAP[clean]
    for code in SUPPORTED_INDIC_LANGUAGES:
        if clean == code.lower():
            return code
    return "hi-IN"


import time


class GnaniTTSService:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: int = 15):
        self.api_key = api_key if api_key is not None else settings.gnani_api_key
        self.base_url = base_url or "https://api.vachana.ai"
        self.timeout = timeout
        self._client: GnaniTTSClient | None = None
        self.last_latency_ms: int | None = None

        if self.api_key:
            try:
                self._client = GnaniTTSClient(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning(f"Could not initialize GnaniTTSClient: {e}")

    async def synthesize_speech(
        self,
        text: str,
        output_path: str | Path,
        language: str = "hi-IN",
        voice: str | None = None,
        model: str = DEFAULT_MODEL,
        persona: str | None = None,
    ) -> Path | None:
        """Synthesize expressive speech using Gnani Timbre v3.0 with inline audio tags.
        
        Args:
            text: Text to synthesize, optionally containing valid Timbre v3.0 audio tags.
            output_path: Destination path for WAV audio file.
            language: Target Indic language code (e.g. hi-IN, ta-IN, kn-IN).
            voice: Exact Timbre v3.0 voice name (e.g. Shivani, Chetana).
            model: Model name, defaults to timbre-v3.0.
            persona: Role/tone alias (e.g. empathetic, conversational, professional).
        """
        t0 = time.time()
        target_file = Path(output_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Resolve voice and persona
        resolved_voice = voice
        if not resolved_voice and persona:
            resolved_voice = VOICE_PERSONAS.get(persona.lower(), DEFAULT_VOICE)
        if not resolved_voice:
            resolved_voice = DEFAULT_VOICE

        # Validate voice against Timbre v3.0 catalog if model is v3.0
        if model == "timbre-v3.0" and resolved_voice not in TIMBRE_V30_VOICES:
            logger.warning(f"Voice {resolved_voice} not in Timbre v3.0 catalog. Defaulting to {DEFAULT_VOICE}.")
            resolved_voice = DEFAULT_VOICE

        lang_code = normalize_language_code(language)
        sanitized_text = sanitize_tags_for_tts(text)

        if self._client:
            import asyncio
            for attempt in range(2):
                try:
                    audio_bytes = await asyncio.to_thread(
                        self._client.synthesize,
                        text=sanitized_text,
                        voice=resolved_voice,
                        model=model,
                        language=lang_code,
                        output_file=target_file,
                    )
                    if audio_bytes and target_file.exists():
                        self.last_latency_ms = int((time.time() - t0) * 1000)
                        return target_file
                except (GnaniTTSError, Exception) as e:
                    if attempt == 0:
                        logger.warning(f"Gnani TTS attempt 1 failed: {e}. Retrying once...")
                        continue
                    logger.warning(f"Gnani TTS call failed after retry: {e}")

        self.last_latency_ms = int((time.time() - t0) * 1000)

        if not self.api_key:
            logger.warning("Gnani TTS API key not configured; skipping audio synthesis")
            return None

        logger.warning(f"Gnani TTS synthesis failed for voice={resolved_voice}, language={lang_code}")
        return None

    async def synthesize_action_summary(
        self,
        output_path: str | Path,
        language: str = "hi-IN",
        custom_text: str | None = None,
    ) -> Path | None:
        """Synthesize action summary using Timbre v3.0 with natural audio tags."""
        is_hindi = language.startswith("hi") or "hinglish" in language.lower()
        if custom_text:
            text = custom_text
        elif is_hindi:
            text = (
                "Aapka legal notice aur escalation package taiyaar hai. <pauses> "
                "Pehla kadam: PDF notice ko brand ke Nodal Officer ko email karein. <pauses> "
                "Doosra kadam: National Consumer Helpline WhatsApp par shikayat darj karein. <pauses> "
                "Teesra kadam: 48 ghante mein samadhan na milne par X par post karein."
            )
        else:
            text = (
                "Your legal demand notice and escalation dossier are ready. <pauses> "
                "Step 1: Email the PDF notice to the brand Nodal Grievance Officer. <pauses> "
                "Step 2: Submit the dispute details to the National Consumer Helpline on WhatsApp. <pauses> "
                "Step 3: Post the public escalation draft on X if unresolved within 48 hours."
            )

        return await self.synthesize_speech(
            text=text,
            output_path=output_path,
            language=language,
            persona="empathetic",
            model="timbre-v3.0",
        )


# Default instance
tts_service = GnaniTTSService()
