import logging
import re
from pathlib import Path
from typing import BinaryIO

from gnani.stt import GnaniSTTClient
from gnani.stt.exceptions import GnaniSTTError
from saarthi.config import settings
from saarthi.speech.gnani_tts import normalize_language_code, SUPPORTED_INDIC_LANGUAGES

logger = logging.getLogger(__name__)


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


import time


class GnaniSTTService:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: int = 15):
        self.api_key = api_key if api_key is not None else settings.gnani_api_key
        self.base_url = base_url or "https://api.vachana.ai"
        self.timeout = timeout
        self._client: GnaniSTTClient | None = None
        self.last_latency_ms: int | None = None

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
        t0 = time.time()
        normalized_lang = normalize_language_code(language_code)

        if self._client:
            import asyncio
            for attempt in range(2):
                try:
                    if isinstance(audio_source, bytes):
                        result = await asyncio.to_thread(
                            self._client.transcribe_bytes,
                            audio_source,
                            filename=filename,
                            language_code=normalized_lang,
                            model=model,
                            format=format,
                        )
                    else:
                        result = await asyncio.to_thread(
                            self._client.transcribe,
                            audio_source,
                            language_code=normalized_lang,
                            model=model,
                            format=format,
                        )

                    transcript = result.get("transcript", "").strip()
                    if transcript:
                        self.last_latency_ms = int((time.time() - t0) * 1000)
                        return transcript, False
                except (GnaniSTTError, Exception) as e:
                    if attempt == 0:
                        logger.warning(f"Gnani STT attempt 1 failed: {e}. Retrying once...")
                        continue
                    logger.warning(f"Gnani STT call failed after retry: {e}")

        self.last_latency_ms = int((time.time() - t0) * 1000)

        if not self.api_key:
            logger.warning(f"Gnani STT API key not configured. Returning empty transcript for {normalized_lang}")
            return "", True

        logger.warning(f"Gnani STT transcription failed for {normalized_lang}")
        return "", True


# Default instance
stt_service = GnaniSTTService()
