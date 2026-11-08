from saarthi.documents.nch_formatter import format_nch_dossier
from saarthi.documents.social_formatter import format_twitter_escalation
from saarthi.domain.calculator import calculate_claim
from datetime import date


def test_nch_formatter():
    claim = calculate_claim(14999.00, date.today(), issue_type="ECOMMERCE_DEFECTIVE_GOODS")
    res = format_nch_dossier(
        complainant_name="Rohan Sharma",
        complainant_contact="rohan@example.com",
        brand_corporate_name="Flipkart Internet Private Limited",
        order_id="OD3091823901",
        incident_date="2026-10-25",
        category="E_COMMERCE",
        claim=claim,
        facts_summary="Delivered phone with broken screen; return denied.",
    )

    dossier = res["dossier_text"]
    assert len(dossier) < 2000
    assert "Flipkart Internet Private Limited" in dossier
    assert "OD3091823901" in dossier
    assert "wa.me/918860005372" in res["whatsapp_url"]


def test_twitter_formatter_character_limit():
    res = format_twitter_escalation(
        brand_handle="@FlipkartSupport",
        order_id="OD3091823901",
        amount_inr=14999.00,
        issue_snippet="Broken phone delivered and support refuses refund",
    )

    tweet = res["tweet_text"]
    assert len(tweet) <= 280
    assert "@FlipkartSupport" in tweet
    assert "@jagograhakjago" in tweet
    assert "@DoCA_GoI" in tweet
    assert "twitter.com/intent/tweet" in res["intent_url"]


def test_twitter_formatter_long_snippet_truncation():
    very_long_snippet = "A" * 350
    res = format_twitter_escalation(
        brand_handle="@FlipkartSupport",
        order_id="OD3091823901",
        amount_inr=14999.00,
        issue_snippet=very_long_snippet,
    )

    assert len(res["tweet_text"]) <= 280


def test_multilingual_disclaimers_cover_all_10_languages():
    from saarthi.telegram.formatters import MULTILINGUAL_DISCLAIMERS, get_legal_disclaimer
    languages = ["hi-IN", "en-IN", "kn-IN", "ta-IN", "te-IN", "mr-IN", "bn-IN", "gu-IN", "ml-IN", "pa-IN"]
    for lang in languages:
        assert lang in MULTILINGUAL_DISCLAIMERS
        disclaimer = get_legal_disclaimer(lang)
        assert len(disclaimer) > 20


def test_assessment_card_branding_and_disclaimer():
    from saarthi.telegram.formatters import format_assessment_card, format_next_steps_card
    state = {
        "preferred_language": "hi-IN",
        "brand_raw": "Flipkart",
        "principal_paise": 1499900,
        "total_claim_paise": 1849900,
        "stt_latency_ms": 150,
        "tts_latency_ms": 280,
    }
    card = format_assessment_card(state)
    assert "Illustrative Pre-Litigation Demand Estimate" in card
    assert "Disclaimer:" in card

    steps = format_next_steps_card(state)
    assert "Next Steps" in steps
    assert "Disclaimer:" in steps


def test_html_injection_escaping():
    from saarthi.telegram.formatters import format_assessment_card, format_cover_email
    malicious_state = {
        "case_reference_id": "SRTH-2026-XSS",
        "complainant_full_name": "<script>alert('pwned')</script>",
        "complainant_contact": "hacker@test.com<img src=x onerror=alert(1)>",
        "brand_raw": "Evil<Vendor>&Co",
        "order_id": "OD<123>&",
        "preferred_language": "en-IN",
    }
    card = format_assessment_card(malicious_state)
    assert "<script>" not in card
    assert "&lt;script&gt;alert(&#x27;pwned&#x27;)&lt;/script&gt;" in card or "&lt;script&gt;" in card
    assert "<img src=x" not in card
    assert "&lt;Vendor&gt;&amp;Co" in card

    email = format_cover_email(malicious_state)
    assert "<script>" not in email
    assert "&lt;script&gt;" in email

