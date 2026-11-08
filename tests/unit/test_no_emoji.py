import re
from datetime import date
from saarthi.telegram.formatters import (
    format_welcome_message,
    format_assessment_card,
    format_cover_email,
    format_next_steps_card,
)
from saarthi.telegram.keyboards import (
    get_persistent_menu_keyboard,
    get_welcome_keyboard,
    get_resume_session_keyboard,
    get_language_keyboard,
    get_voice_character_keyboard,
    get_confirmation_keyboard,
    get_dossier_action_keyboard,
)
from saarthi.documents.nch_formatter import format_nch_dossier
from saarthi.documents.social_formatter import format_twitter_escalation
from saarthi.domain.calculator import calculate_claim
from saarthi.agent.voice_prompts import (
    WELCOME_VOICE_TEMPLATES,
    CLARIFICATION_VOICE_TEMPLATES,
    ASSESSMENT_VOICE_TEMPLATES,
    SINGLE_FIELD_CLARIFICATION_TEMPLATES,
)

# Standard regex for Unicode emoji characters
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u203c\u2049\u20e3\u2122\u2139\u2194-\u2199\u21a9-\u21aa]"
)


def contains_emoji(text: str) -> bool:
    return bool(EMOJI_PATTERN.search(text))


def test_welcome_message_has_no_emoji_and_has_saarthi():
    welcome = format_welcome_message()
    assert not contains_emoji(welcome), f"Emoji found in welcome: {welcome}"
    assert "SAARTHI" in welcome
    assert "saar-thee" in welcome
    assert "ConsumerDost" not in welcome


def test_assessment_card_has_no_emoji():
    claim = calculate_claim(14999.00, date.today(), issue_type="ECOMMERCE_DEFECTIVE_GOODS")
    state = {
        "case_reference_id": "SRTH-2026-TEST",
        "complainant_full_name": "Rohan Sharma",
        "complainant_contact": "rohan@example.com",
        "brand_raw": "Flipkart",
        "principal_paise": claim.principal_paise,
        "calculated_interest_paise": claim.interest_paise,
        "damages_claimed_paise": claim.damages_paise,
        "total_claim_paise": claim.total_demanded_paise,
        "preferred_language": "en-IN",
    }
    card = format_assessment_card(state)
    assert not contains_emoji(card), f"Emoji found in assessment card: {card}"
    assert "SRTH-2026-TEST" in card


def test_cover_email_and_next_steps_have_no_emoji():
    state = {
        "case_reference_id": "SRTH-2026-TEST",
        "complainant_full_name": "Rohan Sharma",
        "complainant_contact": "rohan@example.com",
        "brand_raw": "Flipkart",
        "preferred_language": "en-IN",
    }
    email = format_cover_email(state)
    assert not contains_emoji(email), f"Emoji found in email: {email}"

    next_steps = format_next_steps_card(state)
    assert not contains_emoji(next_steps), f"Emoji found in next steps: {next_steps}"


def test_keyboards_have_no_emoji():
    # Persistent keyboard
    menu = get_persistent_menu_keyboard()
    for row in menu.keyboard:
        for btn in row:
            assert not contains_emoji(btn.text), f"Emoji in persistent button: {btn.text}"

    # Inline keyboards
    inline_kbs = [
        get_welcome_keyboard(),
        get_resume_session_keyboard(),
        get_language_keyboard(),
        get_voice_character_keyboard(),
        get_confirmation_keyboard(),
        get_dossier_action_keyboard("https://wa.me/test", "https://twitter.com/test"),
    ]
    for ikb in inline_kbs:
        for row in ikb.inline_keyboard:
            for btn in row:
                assert not contains_emoji(btn.text), f"Emoji in inline button: {btn.text}"


def test_dossiers_have_no_emoji():
    claim = calculate_claim(14999.00, date.today(), issue_type="ECOMMERCE_DEFECTIVE_GOODS")
    nch = format_nch_dossier(
        complainant_name="Rohan Sharma",
        complainant_contact="rohan@example.com",
        brand_corporate_name="Flipkart Internet Private Limited",
        order_id="OD123",
        incident_date="2026-10-25",
        category="E_COMMERCE",
        claim=claim,
        facts_summary="Broken screen",
    )
    assert not contains_emoji(nch["dossier_text"])
    assert "SAARTHI" in nch["dossier_text"]

    social = format_twitter_escalation(
        brand_handle="@FlipkartSupport",
        order_id="OD123",
        amount_inr=14999.0,
        issue_snippet="Broken phone delivered",
    )
    assert not contains_emoji(social["tweet_text"])


def test_voice_prompts_have_no_emoji():
    for text in WELCOME_VOICE_TEMPLATES.values():
        assert not contains_emoji(text)
    for text in CLARIFICATION_VOICE_TEMPLATES.values():
        assert not contains_emoji(text)
    for text in ASSESSMENT_VOICE_TEMPLATES.values():
        assert not contains_emoji(text)
    for lang_dict in SINGLE_FIELD_CLARIFICATION_TEMPLATES.values():
        for text in lang_dict.values():
            assert not contains_emoji(text)
