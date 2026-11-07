import pytest
from unittest.mock import MagicMock
from consumerdost.speech.gnani_stt import (
    GnaniSTTService,
    detect_indic_script_language,
    GOLDEN_DEMO_TRANSCRIPTS,
)


def test_detect_indic_script_language():
    # Kannada
    assert detect_indic_script_language("ನಾನು ಫ್ಲಿಪ್‌ಕಾರ್ಟ್‌ನಿಂದ ಫೋನ್ ಆರ್ಡರ್ ಮಾಡಿದ್ದೆ") == "kn-IN"
    # Tamil
    assert detect_indic_script_language("நான் ஃபிளிப்கார்ட்டில் போன் வாங்கினேன்") == "ta-IN"
    # Telugu
    assert detect_indic_script_language("నేను ఫ్లిప్‌కార్ట్ నుండి ఫోన్ ఆర్డర్ చేసాను") == "te-IN"
    # Hindi / Devanagari
    assert detect_indic_script_language("मैंने फ्लिपकार्ट से फोन मंगवाया था") == "hi-IN"
    # English
    assert detect_indic_script_language("I ordered a phone from Flipkart on 25th October") == "en-IN"


@pytest.mark.asyncio
async def test_transcribe_audio_multilingual_client():
    mock_client = MagicMock()
    mock_client.transcribe_bytes.return_value = {
        "transcript": "ನನ್ನ ಆರ್ಡರ್ ತಲುಪಿಲ್ಲ"
    }

    service = GnaniSTTService(api_key="test_api_key")
    service._client = mock_client

    transcript, is_fallback = await service.transcribe_audio(
        audio_source=b"dummy audio bytes",
        language_code="kn-IN",
    )

    assert transcript == "ನನ್ನ ಆರ್ಡರ್ ತಲುಪಿಲ್ಲ"
    assert is_fallback is False
    mock_client.transcribe_bytes.assert_called_once()
    assert mock_client.transcribe_bytes.call_args[1]["language_code"] == "kn-IN"


@pytest.mark.asyncio
async def test_transcribe_audio_demo_fallback():
    service = GnaniSTTService(api_key=None)

    transcript_kn, is_fallback = await service.transcribe_audio(
        audio_source=b"dummy",
        language_code="kannada",
    )
    assert is_fallback is True
    assert transcript_kn == GOLDEN_DEMO_TRANSCRIPTS["kn-IN"]

    transcript_ta, is_fallback = await service.transcribe_audio(
        audio_source=b"dummy",
        language_code="tamil",
    )
    assert is_fallback is True
    assert transcript_ta == GOLDEN_DEMO_TRANSCRIPTS["ta-IN"]
