from consumerdost.agent.voice_prompts import (
    VoicePromptComposer,
    WELCOME_VOICE_TEMPLATES,
    CLARIFICATION_VOICE_TEMPLATES,
    ASSESSMENT_VOICE_TEMPLATES,
)
from consumerdost.speech.tags import validate_tags


def test_templates_cover_all_10_indic_languages():
    languages = ["hi-IN", "en-IN", "kn-IN", "ta-IN", "te-IN", "mr-IN", "bn-IN", "gu-IN", "ml-IN", "pa-IN"]
    for lang in languages:
        assert lang in WELCOME_VOICE_TEMPLATES
        assert lang in CLARIFICATION_VOICE_TEMPLATES
        assert lang in ASSESSMENT_VOICE_TEMPLATES


def test_audio_tags_in_welcome_prompts():
    for lang, prompt in WELCOME_VOICE_TEMPLATES.items():
        is_valid, invalid = validate_tags(prompt)
        assert is_valid, f"Invalid tags in welcome prompt for {lang}: {invalid}"
        assert "<excited>" in prompt
        assert "<pauses>" in prompt


def test_audio_tags_in_clarification_prompts():
    for lang, prompt in CLARIFICATION_VOICE_TEMPLATES.items():
        is_valid, invalid = validate_tags(prompt)
        assert is_valid, f"Invalid tags in clarification prompt for {lang}: {invalid}"
        assert "<sigh>" in prompt
        assert "<pauses>" in prompt
        assert "<whispers>" in prompt


def test_compose_assessment_amount_formatting():
    prompt_hi = VoicePromptComposer.compose_assessment(17499.50, language="hi-IN")
    assert "17,499.50" in prompt_hi
    assert "<excited>" in prompt_hi
    assert "<pauses>" in prompt_hi
    is_valid, invalid = validate_tags(prompt_hi)
    assert is_valid, f"Invalid tags in assessment prompt: {invalid}"

    prompt_kn = VoicePromptComposer.compose_assessment(25000, language="kannada")
    assert "25,000.00" in prompt_kn
    is_valid, invalid = validate_tags(prompt_kn)
    assert is_valid
