import logging
from pathlib import Path

from gnani.tts import GnaniTTSClient
from gnani.tts.exceptions import GnaniTTSError
from consumerdost.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTS_TEXT_HI = (
    "Aapka legal notice aur escalation package taiyaar hai. "
    "Pehla kadam: PDF notice ko brand ke Nodal Officer ko email karein. "
    "Doosra kadam: National Consumer Helpline WhatsApp par shikayat darj karein. "
    "Teesra kadam: 48 ghante mein samadhan na milne par X par post karein."
)

DEFAULT_TTS_TEXT_EN = (
    "Your legal demand notice and escalation dossier are ready. "
    "Step 1: Email the PDF notice to the brand Nodal Grievance Officer. "
    "Step 2: Submit the dispute details to the National Consumer Helpline on WhatsApp. "
    "Step 3: Post the public escalation draft on X if unresolved within 48 hours."
)


class GnaniTTSService:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: int = 5):
        self.api_key = api_key or settings.gnani_api_key
        self.base_url = base_url or "https://api.vachana.ai"
        self.timeout = timeout
        self._client: GnaniTTSClient | None = None

        if self.api_key:
            try:
                self._client = GnaniTTSClient(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                )
            except Exception as e:
                logger.warning(f"Could not initialize GnaniTTSClient: {e}")

    async def synthesize_action_summary(
        self,
        output_path: str | Path,
        language: str = "hi-IN",
        custom_text: str | None = None,
    ) -> Path | None:
        """Synthesize a 15-20 second voice action summary using Gnani Timbre TTS."""
        target_file = Path(output_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        is_hindi = language.startswith("hi") or "hinglish" in language.lower()
        text = custom_text or (DEFAULT_TTS_TEXT_HI if is_hindi else DEFAULT_TTS_TEXT_EN)
        voice = "Nalini" if is_hindi else "Pranav"
        lang_code = "hi-IN" if is_hindi else "en-IN"

        if self._client:
            try:
                audio_bytes = self._client.synthesize(
                    text=text,
                    voice=voice,
                    model="timbre-v2.5",
                    language=lang_code,
                    output_file=target_file,
                )
                if audio_bytes and target_file.exists():
                    return target_file
            except GnaniTTSError as e:
                logger.warning(f"Gnani TTS API error: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error calling Gnani TTS: {e}")

        # In demo mode if synthesis failed, write a dummy wav/mp3 header or skip
        if settings.demo_mode:
            logger.info("Demo mode: Writing placeholder audio response for TTS summary")
            # Write a minimal valid RIFF WAV header (44 bytes silent audio)
            wav_header = (
                b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            )
            target_file.write_bytes(wav_header)
            return target_file

        return None


# Default instance
tts_service = GnaniTTSService()
