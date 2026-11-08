from saarthi.agent.voice_prompts import (
    VoicePromptComposer,
    WELCOME_VOICE_TEMPLATES,
    CLARIFICATION_VOICE_TEMPLATES,
    ASSESSMENT_VOICE_TEMPLATES,
    SINGLE_FIELD_CLARIFICATION_TEMPLATES,
)
from saarthi.speech.tags import validate_tags, extract_tags


def test_templates_cover_all_10_indic_languages():
    languages = ["hi-IN", "en-IN", "kn-IN", "ta-IN", "te-IN", "mr-IN", "bn-IN", "gu-IN", "ml-IN", "pa-IN"]
    for lang in languages:
        assert lang in WELCOME_VOICE_TEMPLATES
        assert lang in CLARIFICATION_VOICE_TEMPLATES
        assert lang in ASSESSMENT_VOICE_TEMPLATES


def test_no_leading_emotional_tags_in_welcome_prompts():
    for lang, prompt in WELCOME_VOICE_TEMPLATES.items():
        assert not prompt.strip().startswith("<excited>"), f"Leading <excited> in {lang}"
        assert not prompt.strip().startswith("<sigh>"), f"Leading <sigh> in {lang}"
        assert not prompt.strip().startswith("<whispers>"), f"Leading <whispers> in {lang}"
        # No disallowed tags anywhere
        assert "<excited>" not in prompt
        assert "<sigh>" not in prompt
        assert "<whispers>" not in prompt
        # Verify tag count <= 2
        tags = extract_tags(prompt)
        assert len(tags) <= 2, f"Too many tags in {lang}: {tags}"
        # Verify valid
        is_valid, violations = validate_tags(prompt)
        assert is_valid, f"Violations in {lang}: {violations}"


def test_no_emotional_tags_in_clarification_prompts():
    for lang, prompt in CLARIFICATION_VOICE_TEMPLATES.items():
        assert "<sigh>" not in prompt
        assert "<excited>" not in prompt
        assert "<whispers>" not in prompt
        tags = extract_tags(prompt)
        assert len(tags) <= 2, f"Too many tags in clarification for {lang}: {tags}"
        is_valid, violations = validate_tags(prompt)
        assert is_valid, f"Violations in clarification for {lang}: {violations}"


def test_compose_assessment_amount_formatting():
    prompt_hi = VoicePromptComposer.compose_assessment(17499.50, language="hi-IN")
    assert "17,499.50" in prompt_hi
    assert "<excited>" not in prompt_hi
    assert "<pauses>" in prompt_hi
    is_valid, violations = validate_tags(prompt_hi)
    assert is_valid, f"Invalid tags in assessment prompt: {violations}"

    prompt_kn = VoicePromptComposer.compose_assessment(25000, language="kannada")
    assert "25,000.00" in prompt_kn
    is_valid, violations = validate_tags(prompt_kn)
    assert is_valid


def test_single_field_clarification_tags():
    for field, lang_map in SINGLE_FIELD_CLARIFICATION_TEMPLATES.items():
        for lang, prompt in lang_map.items():
            assert "<whispers>" not in prompt
            assert "<sigh>" not in prompt
            assert "<excited>" not in prompt
            is_valid, violations = validate_tags(prompt)
            assert is_valid, f"Invalid tags in single field prompt for {field}/{lang}: {violations}"

    # Verify composition
    hi_name = VoicePromptComposer.compose_single_field_clarification("full_name", "hi-IN")
    assert "naam" in hi_name.lower() or "नाम" in hi_name
    en_order = VoicePromptComposer.compose_single_field_clarification("order_id", "en-IN")
    assert "order id" in en_order.lower()


def test_welcome_prompt_gender_pronouns_and_verbs():
    # Female voices must use feminine verb endings (karungi)
    hi_female_shivani = VoicePromptComposer.compose_welcome("hi-IN", voice="Shivani")
    assert "taiyaar karungi" in hi_female_shivani
    assert "karunga" not in hi_female_shivani

    hi_female_chetana = VoicePromptComposer.compose_welcome("hi-IN", voice="Chetana")
    assert "taiyaar karungi" in hi_female_chetana
    assert "karunga" not in hi_female_chetana

    # Male voice must use masculine verb endings (karunga)
    hi_male_devansh = VoicePromptComposer.compose_welcome("hi-IN", voice="Devansh")
    assert "taiyaar karunga" in hi_male_devansh
    assert "karungi" not in hi_male_devansh

    # Punjabi gender agreement
    pa_female = VoicePromptComposer.compose_welcome("pa-IN", voice="Shivani")
    assert "ਕਰਾਂਗੀ" in pa_female
    pa_male = VoicePromptComposer.compose_welcome("pa-IN", voice="Devansh")
    assert "ਕਰਾਂਗਾ" in pa_male
