import pytest
import tempfile
from pathlib import Path
import respx
import httpx

from consumerdost.speech.gnani_stt import GnaniSTTService, GOLDEN_DEMO_TRANSCRIPT
from consumerdost.speech.gnani_tts import GnaniTTSService


@pytest.mark.asyncio
async def test_gnani_stt_demo_fallback_when_api_fails():
    # Use invalid key to trigger fallback
    service = GnaniSTTService(api_key="invalid_test_key", timeout=1)
    transcript, is_fallback = await service.transcribe_audio(
        audio_source=b"fake_pcm_data_here",
        filename="test.ogg",
        language_code="hi-IN",
    )

    assert is_fallback is True
    assert transcript == GOLDEN_DEMO_TRANSCRIPT


@pytest.mark.asyncio
async def test_gnani_tts_demo_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = Path(tmpdir) / "action_summary.wav"
        service = GnaniTTSService(api_key="invalid_test_key", timeout=1)

        result_path = await service.synthesize_action_summary(
            output_path=out_file,
            language="hi-IN",
        )

        assert result_path is not None
        assert result_path.exists()
        assert result_path.stat().st_size > 0
