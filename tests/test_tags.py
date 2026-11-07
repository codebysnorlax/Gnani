from consumerdost.speech.tags import (
    SUPPORTED_AUDIO_TAGS,
    extract_tags,
    is_valid_tag,
    validate_tags,
    sanitize_tags_for_tts,
    strip_audio_tags,
)


def test_supported_audio_tags_catalog():
    expected_tags = {
        "<coughs>",
        "<excited>",
        "<exhales>",
        "<giggle>",
        "<laugh>",
        "<pauses>",
        "<shouting>",
        "<sigh>",
        "<slow>",
        "<sniffles>",
        "<whispers>",
        "<yawns>",
        "<clears throat>",
    }
    assert SUPPORTED_AUDIO_TAGS == expected_tags
    assert len(SUPPORTED_AUDIO_TAGS) == 13


def test_extract_tags():
    sample = "Hello! <excited> We have received your claim. <pauses> Let me check the details."
    tags = extract_tags(sample)
    assert tags == ["<excited>", "<pauses>"]


def test_validate_tags_valid():
    sample = "<sigh> Brand ne refund deny kiya. <pauses> Tension mat lijiye."
    is_valid, invalid = validate_tags(sample)
    assert is_valid is True
    assert invalid == []


def test_validate_tags_invalid():
    sample = "Look at this <invalid_tag> and <Laughs Harder>."
    is_valid, invalid = validate_tags(sample)
    assert is_valid is False
    assert "<invalid_tag>" in invalid
    assert "<Laughs Harder>" in invalid


def test_sanitize_tags_for_tts():
    # Capitalized valid tags should be normalized to lower case; invalid tags should be stripped
    sample = "Start <Excited> awesome news <FakeTag> end <PAUSES> now."
    sanitized = sanitize_tags_for_tts(sample)
    assert "<excited>" in sanitized
    assert "<pauses>" in sanitized
    assert "<FakeTag>" not in sanitized
    assert "<faketag>" not in sanitized


def test_strip_audio_tags():
    sample = "Namaste! <excited> Main hoon ConsumerDost. <pauses> <sigh> Aapka dispute sunkar hal nikalenge."
    clean = strip_audio_tags(sample)
    assert "<" not in clean
    assert ">" not in clean
    assert clean == "Namaste! Main hoon ConsumerDost. Aapka dispute sunkar hal nikalenge."
