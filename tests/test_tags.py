from saarthi.speech.tags import (
    ALLOWED_AUDIO_TAGS,
    SUPPORTED_AUDIO_TAGS,
    MAX_TAGS_PER_RESPONSE,
    extract_tags,
    is_valid_tag,
    validate_tags,
    sanitize_tags_for_tts,
    strip_audio_tags,
)


def test_supported_audio_tags_catalog():
    expected_tags = {
        "<pauses>",
        "<slow>",
    }
    assert ALLOWED_AUDIO_TAGS == expected_tags
    assert SUPPORTED_AUDIO_TAGS == expected_tags
    assert len(ALLOWED_AUDIO_TAGS) == 2
    assert MAX_TAGS_PER_RESPONSE == 2


def test_extract_tags():
    sample = "Hello! We have received your claim. <pauses> <slow> Let me check."
    tags = extract_tags(sample)
    assert tags == ["<pauses>", "<slow>"]


def test_validate_tags_valid():
    sample = "Claim received. <pauses> Checking statutory clauses. <slow>"
    is_valid, violations = validate_tags(sample)
    assert is_valid is True
    assert violations == []


def test_validate_tags_invalid():
    # 1. Unsupported tag
    sample1 = "Look at this <sigh> and <excited>."
    is_valid1, violations1 = validate_tags(sample1)
    assert is_valid1 is False
    assert any("unsupported:<sigh>" in v for v in violations1)

    # 2. Leading tag prohibited
    sample2 = "<pauses> Hello there."
    is_valid2, violations2 = validate_tags(sample2)
    assert is_valid2 is False
    assert "leading_tag_prohibited" in violations2

    # 3. Exceeds max 2 tags
    sample3 = "One <pauses> two <slow> three <pauses>"
    is_valid3, violations3 = validate_tags(sample3)
    assert is_valid3 is False
    assert any("tag_count_exceeded" in v for v in violations3)


def test_sanitize_tags_for_tts():
    # 1. Strips leading tag
    # 2. Normalizes allowed tag to lower case
    # 3. Strips unsupported tag
    # 4. Caps at max 2 tags
    sample = "<excited> Start <PAUSES> middle <invalid> and <SLOW> extra <pauses> end."
    sanitized = sanitize_tags_for_tts(sample, max_tags=2)
    assert not sanitized.startswith("<")
    assert "<pauses>" in sanitized
    assert "<slow>" in sanitized
    assert "<excited>" not in sanitized
    assert "<invalid>" not in sanitized
    # Count tags
    extracted = extract_tags(sanitized)
    assert len(extracted) <= 2


def test_strip_audio_tags():
    sample = "Namaste! Main hoon SAARTHI. <pauses> <slow> Aapka dispute hal karenge."
    clean = strip_audio_tags(sample)
    assert "<" not in clean
    assert ">" not in clean
    assert clean == "Namaste! Main hoon SAARTHI. Aapka dispute hal karenge."
