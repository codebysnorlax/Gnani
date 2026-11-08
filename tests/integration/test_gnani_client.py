import pytest
import tempfile
from pathlib import Path
import respx
import httpx

from saarthi.speech.gnani_stt import GnaniSTTService
from saarthi.speech.gnani_tts import GnaniTTSService


@pytest.mark.asyncio
async def test_gnani_stt_honest_failure_when_api_fails():
    # Use invalid key to trigger failure
    service = GnaniSTTService(api_key="invalid_test_key", timeout=1)
    transcript, is_fallback = await service.transcribe_audio(
        audio_source=b"fake_pcm_data_here",
        filename="test.ogg",
        language_code="hi-IN",
    )

    assert is_fallback is True
    assert transcript == ""


@pytest.mark.asyncio
async def test_gnani_tts_honest_failure_when_api_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "action_summary.wav"
        service = GnaniTTSService(api_key="invalid_test_key", timeout=1)

        result_path = await service.synthesize_action_summary(
            output_path=out_file,
            language="hi-IN",
        )

        # Honest failure: does not write silent placeholder WAV; returns None
        assert result_path is None
        assert not out_file.exists()
