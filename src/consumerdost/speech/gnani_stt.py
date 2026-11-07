import logging
import re
from pathlib import Path
from typing import BinaryIO

from gnani.stt import GnaniSTTClient
from gnani.stt.exceptions import GnaniSTTError
from consumerdost.config import settings
from consumerdost.speech.gnani_tts import normalize_language_code, SUPPORTED_INDIC_LANGUAGES

logger = logging.getLogger(__name__)

GOLDEN_DEMO_TRANSCRIPTS: dict[str, str] = {
    "hi-IN": (
        "Bhaiya maine Flipkart se 14,999 ka phone mangaya tha 25 October ko. "
        "Box khola toh screen tooti hui thi. Order ID OD3091823901. "
        "Customer care bol raha hai return nahi hoga."
    ),
    "en-IN": (
        "I ordered a mobile phone worth 14,999 rupees from Flipkart on 25th October. "
        "The screen was broken on delivery. Order ID OD3091823901. "
        "Customer support refused my return request."
    ),
    "kn-IN": (
        "ನಾನು ಫ್ಲಿಪ್‌ಕಾರ್ಟ್‌ನಿಂದ 14,999 ರೂಪಾಯಿಗೆ ಫೋನ್ ಆರ್ಡರ್ ಮಾಡಿದ್ದೆ. "
        "ಸ್ಕ್ರೀನ್ ಒಡೆದುಹೋಗಿದೆ. ಆರ್ಡರ್ ಐಡಿ OD3091823901. "
        "ಗ್ರಾಹಕ ಸೇವೆ ರಿಟರ್ನ್ ನಿರಾಕರಿಸಿದೆ."
    ),
    "ta-IN": (
        "நான் ஃபிளிப்கார்ட்டில் 14,999 ரூபாய்க்கு போன் வாங்கினேன். "
        "திரை உடைந்திருந்தது. ஆர்டர் ஐடி OD3091823901. "
        "வாடிக்கையாளர் சேவை மாற்ற மறுக்கிறது."
    ),
    "te-IN": (
        "నేను ఫ్లిప్‌కార్ట్ నుండి 14,999 రూపాయల ఫోన్ ఆర్డర్ చేసాను. "
        "స్క్రీన్ పగిలిపోయింది. ఆర్డర్ ఐడీ OD3091823901. "
        "కస్టమర్ కేర్ రిటర్న్ నిరాకరించింది."
    ),
    "mr-IN": (
        "मी फ्लिपकार्टवरून 14,999 रुपयांचा फोन मागवला होता. "
        "स्क्रीन तुटलेली आली. ऑर्डर आयडी OD3091823901. "
        "कस्टमर केअर रिटर्न नाकारत आहे."
    ),
}

GOLDEN_DEMO_TRANSCRIPT: str = GOLDEN_DEMO_TRANSCRIPTS["hi-IN"]


def detect_indic_script_language(text: str) -> str:
    """Detect Indic language from Unicode script ranges."""
    if not text:
        return "hi-IN"

    # Unicode ranges for Indic scripts
    kannada_count = len(re.findall(r"[\u0C80-\u0CFF]", text))
    tamil_count = len(re.findall(r"[\u0B80-\u0BFF]", text))
    telugu_count = len(re.findall(r"[\u0C00-\u0C7F]", text))
    malayalam_count = len(re.findall(r"[\u0D00-\u0D7F]", text))
    bengali_count = len(re.findall(r"[\u0980-\u09FF]", text))
    gujarati_count = len(re.findall(r"[\u0A80-\u0AFF]", text))
    punjabi_count = len(re.findall(r"[\u0A00-\u0A7F]", text))
    devanagari_count = len(re.findall(r"[\u0900-\u097F]", text))

    counts = {
        "kn-IN": kannada_count,
        "ta-IN": tamil_count,
        "te-IN": telugu_count,
        "ml-IN": malayalam_count,
        "bn-IN": bengali_count,
        "gu-IN": gujarati_count,
        "pa-IN": punjabi_count,
        "hi-IN": devanagari_count,
    }

    best_lang, best_count = max(counts.items(), key=lambda item: item[1])
    if best_count > 3:
        return best_lang

    # Check for English / Latin script
    latin_count = len(re.findall(r"[a-zA-Z]", text))
    if latin_count > 10:
        return "en-IN"

    return "hi-IN"


class GnaniSTTService:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: int = 5):
        self.api_key = api_key or settings.gnani_api_key
        self.base_url = base_url or "https://api.vachana.ai"
        self.timeout = timeout
        self._client: GnaniSTTClient | None = None

        if self.api_key:
            try:
                self._client = GnaniSTTClient(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning(f"Could not initialize GnaniSTTClient: {e}")

    async def transcribe_audio(
        self,
        audio_source: str | Path | bytes | BinaryIO,
        filename: str = "audio.ogg",
        language_code: str = "hi-IN",
        model: str = "prisma-v3.0",
        format: str = "transcribe",
    ) -> tuple[str, bool]:
        """Transcribe audio using Gnani Prisma v3.0 STT with inverse text normalization.
        
        Returns tuple of (transcript_text, is_fallback).
        """
        normalized_lang = normalize_language_code(language_code)

        if self._client:
            try:
                if isinstance(audio_source, bytes):
                    result = self._client.transcribe_bytes(
                        audio_source,
                        filename=filename,
                        language_code=normalized_lang,
                        model=model,
                        format=format,
                    )
                else:
                    result = self._client.transcribe(
                        audio_source,
                        language_code=normalized_lang,
                        model=model,
                        format=format,
                    )

                transcript = result.get("transcript", "").strip()
                if transcript:
                    return transcript, False
            except GnaniSTTError as e:
                logger.warning(f"Gnani STT API error: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error calling Gnani STT: {e}")

        # Fallback to demo fixture if in DEMO_MODE or when API is unavailable
        if settings.demo_mode or not self.api_key:
            logger.info(f"Serving multilingual demo transcript for {normalized_lang}")
            transcript = GOLDEN_DEMO_TRANSCRIPTS.get(
                normalized_lang, GOLDEN_DEMO_TRANSCRIPTS["hi-IN"]
            )
            return transcript, True

        return "", True


# Default instance
stt_service = GnaniSTTService()
