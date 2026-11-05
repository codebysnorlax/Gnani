from consumerdost.documents.nch_formatter import format_nch_dossier
from consumerdost.documents.social_formatter import format_twitter_escalation
from consumerdost.domain.calculator import calculate_claim
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
