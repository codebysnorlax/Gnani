import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from saarthi.speech.gnani_tts import (
    GnaniTTSService,
    SUPPORTED_INDIC_LANGUAGES,
    VOICE_PERSONAS,
    normalize_language_code,
)


def test_supported_indic_languages():
    assert len(SUPPORTED_INDIC_LANGUAGES) == 10
    assert "hi-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "kn-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "ta-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "te-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "mr-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "bn-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "gu-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "ml-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "pa-IN" in SUPPORTED_INDIC_LANGUAGES
    assert "en-IN" in SUPPORTED_INDIC_LANGUAGES


def test_normalize_language_code():
    assert normalize_language_code("kannada") == "kn-IN"
    assert normalize_language_code("TAMIL") == "ta-IN"
    assert normalize_language_code("te") == "te-IN"
    assert normalize_language_code("hindi") == "hi-IN"
    assert normalize_language_code(None) == "hi-IN"
    assert normalize_language_code("unknown") == "hi-IN"


def test_persona_mapping():
    assert VOICE_PERSONAS["empathetic"] == "Shivani"
    assert VOICE_PERSONAS["conversational"] == "Devansh"
    assert VOICE_PERSONAS["care"] == "Chetana"


@pytest.mark.asyncio
async def test_synthesize_speech_with_audio_tags(tmp_path: Path):
    mock_client = MagicMock()
    output_wav = tmp_path / "test_output.wav"
    
    # Mock synthesize returning bytes and creating file
    def fake_synthesize(text, voice, model, language, output_file):
        Path(output_file).write_bytes(b"RIFF dummy wav data")
        return b"RIFF dummy wav data"

    mock_client.synthesize.side_effect = fake_synthesize

    service = GnaniTTSService(api_key="test_key")
    service._client = mock_client

    sample_text = "Namaste! SAARTHI is here. <pauses> <slow> How can I help?"
    result = await service.synthesize_speech(
        text=sample_text,
        output_path=output_wav,
        language="kn-IN",
        persona="empathetic",
        model="timbre-v3.0",
    )

    assert result == output_wav
    assert output_wav.exists()
    mock_client.synthesize.assert_called_once()
    call_args = mock_client.synthesize.call_args[1]
    assert call_args["voice"] == "Shivani"
    assert call_args["model"] == "timbre-v3.0"
    assert call_args["language"] == "kn-IN"
    assert "<pauses>" in call_args["text"]
    assert "<slow>" in call_args["text"]


@pytest.mark.asyncio
async def test_synthesize_speech_honest_failure_no_key(tmp_path: Path):
    # Without client / API key, should return None instead of writing silent placeholder WAV
    output_wav = tmp_path / "fallback.wav"
    service = GnaniTTSService(api_key="")

    result = await service.synthesize_speech(
        text="Hello test",
        output_path=output_wav,
        language="hi-IN",
    )
    assert result is None
    assert not output_wav.exists()


@pytest.mark.asyncio
async def test_tts_retry_on_failure(tmp_path: Path):
    from gnani.tts.exceptions import GnaniTTSError

    mock_client = MagicMock()
    output_wav = tmp_path / "retry_output.wav"

    calls = 0
    def side_effect(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise GnaniTTSError("Network timeout")
        output_wav.write_bytes(b"RIFF retried wav data")
        return b"RIFF retried wav data"

    mock_client.synthesize.side_effect = side_effect

    service = GnaniTTSService(api_key="test_key", timeout=15)
    service._client = mock_client
    assert service.timeout == 15

    result = await service.synthesize_speech(
        text="Retry test",
        output_path=output_wav,
        language="hi-IN",
    )
    assert result == output_wav
    assert calls == 2
    assert service.last_latency_ms is not None


@pytest.mark.asyncio
async def test_stt_retry_on_failure():
    from saarthi.speech.gnani_stt import GnaniSTTService
    from gnani.stt.exceptions import GnaniSTTError

    mock_client = MagicMock()
    calls = 0
    def side_effect(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise GnaniSTTError("Connection reset")
        return {"transcript": "Retried STT success transcript"}

    mock_client.transcribe_bytes.side_effect = side_effect

    service = GnaniSTTService(api_key="test_key", timeout=15)
    service._client = mock_client
    assert service.timeout == 15

    transcript, is_fallback = await service.transcribe_audio(
        audio_source=b"fake audio",
        language_code="hi-IN",
    )
    assert transcript == "Retried STT success transcript"
    assert is_fallback is False
    assert calls == 2
    assert service.last_latency_ms is not None
