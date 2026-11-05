import logging
import hashlib
from pathlib import Path
from typing import BinaryIO

from gnani.stt import GnaniSTTClient
from gnani.stt.exceptions import GnaniSTTError
from consumerdost.config import settings

logger = logging.getLogger(__name__)

GOLDEN_DEMO_TRANSCRIPT = (
    "Bhaiya maine Flipkart se 14,999 ka phone mangaya tha 25 October ko. "
    "Box khola toh screen tooti hui thi. Order ID OD3091823901. "
    "Customer care bol raha hai return nahi hoga."
)


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
        """Transcribe audio using Gnani Prisma v3.0 STT with ITN.
        
        Returns tuple of (transcript_text, is_fallback).
        """
        # If no client or demo mode fallback trigger
        if self._client:
            try:
                if isinstance(audio_source, bytes):
                    result = self._client.transcribe_bytes(
                        audio_source,
                        filename=filename,
                        language_code=language_code,
                        model=model,
                        format=format,
                    )
                else:
                    result = self._client.transcribe(
                        audio_source,
                        language_code=language_code,
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

        # Fallback to demo fixture if in DEMO_MODE or when API unavailable
        if settings.demo_mode:
            logger.info("Serving Golden Demo fixture transcript under DEMO_MODE")
            return GOLDEN_DEMO_TRANSCRIPT, True

        return "", True


# Default instance
stt_service = GnaniSTTService()
