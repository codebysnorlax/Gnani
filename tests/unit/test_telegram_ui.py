from consumerdost.telegram.keyboards import (
    get_welcome_keyboard,
    get_confirmation_keyboard,
    get_dossier_action_keyboard,
)
from consumerdost.telegram.formatters import (
    format_welcome_message,
    format_assessment_card,
    format_cover_email,
)
from consumerdost.agent.state import ConsumerDostState


def test_keyboards():
    w = get_welcome_keyboard()
    assert len(w.inline_keyboard) == 3

    c = get_confirmation_keyboard()
    assert len(c.inline_keyboard) == 2

    d = get_dossier_action_keyboard("https://wa.me/123", "https://twitter.com/456")
    assert len(d.inline_keyboard) == 3


def test_formatters():
    msg = format_welcome_message()
    assert "ConsumerDost" in msg
    assert "Section 35" in msg

    state: ConsumerDostState = {
        "case_reference_id": "CD-2026-TEST",
        "complainant_full_name": "Rohan Sharma",
        "complainant_contact": "rohan@example.com",
        "brand_resolved": {
            "canonical_name": "FLIPKART",
            "aliases": ["flipkart"],
            "corporate_name": "Flipkart Internet Private Limited",
            "registered_address": "Bengaluru",
            "nodal_officer_name": "Grievance Officer",
            "nodal_email": "grievance@flipkart.com",
            "twitter_handle": "@FlipkartSupport",
            "category": "E_COMMERCE",
        },
        "order_id": "OD123",
        "incident_date": "2026-10-25",
        "principal_paise": 1499900,
        "total_claim_paise": 2003229,
    }

    card = format_assessment_card(state)
    assert "Flipkart Internet Private Limited" in card
    assert "₹20,032.29" in card
    assert "OD123" in card

    email_block = format_cover_email(state)
    assert "grievance@flipkart.com" in email_block
    assert "OD123" in email_block
