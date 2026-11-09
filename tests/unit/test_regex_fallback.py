import pytest
from saarthi.agent.regex_fallback import extract_entities_regex


def test_regex_extraction_flipkart_hindi():
    text = "Maine Flipkart se 14999 ka phone mangaya tha 25 October ko. Box me toota screen nikla. Order ID OD3091823901."
    draft = extract_entities_regex(text)

    assert draft.amount_paid_inr == 14999.0
    assert draft.brand_raw == "Flipkart Internet Private Limited"
    assert draft.order_id == "OD3091823901"
    assert draft.issue_type == "ECOMMERCE_DEFECTIVE_GOODS"
    assert draft.category == "E_COMMERCE"
    assert "2026-10-25" in str(draft.incident_date) or "10-25" in str(draft.incident_date)
    assert "Flipkart Internet Private Limited" in draft.incident_summary


def test_regex_extraction_upi_hindi():
    text = "Mera 1200 rupees ka UPI recharge fail ho gaya kal. UTR: 123456789012 bank debit ho gaya."
    draft = extract_entities_regex(text)

    assert draft.amount_paid_inr == 1200.0
    assert draft.issue_type == "UPI_FAILED_DEBIT_STUCK"
    assert draft.category == "FINTECH_UPI"
    assert draft.order_id == "123456789012"


def test_regex_extraction_airline():
    text = "Indigo flight cancelled without prior notice. Amount was Rs 6500. PNR 98765432."
    draft = extract_entities_regex(text)

    assert draft.amount_paid_inr == 6500.0
    assert draft.issue_type == "AIRLINE_CANCELLED_OR_DELAYED"
    assert draft.category == "AIRLINES"
    assert draft.incident_date is None


def test_unstated_date_is_none():
    text = "Maine Flipkart se 5000 rs ka samaan mangaya."
    draft = extract_entities_regex(text)
    assert draft.incident_date is None
    assert "incident_date" in draft.missing_critical_fields


def test_conversational_and_ordinal_dates():
    from saarthi.agent.regex_fallback import parse_date_from_text
    from datetime import date, timedelta

    today = date.today()
    y = today.year

    # Ordinal day-first
    assert parse_date_from_text("25th October") == f"{y:04d}-10-25"
    assert parse_date_from_text("25 Oct") == f"{y:04d}-10-25"
    assert parse_date_from_text("1st January 2025") == "2025-01-01"

    # Month-first
    assert parse_date_from_text("October 25th") == f"{y:04d}-10-25"
    assert parse_date_from_text("Oct 25, 2026") == "2026-10-25"

    # Relative
    assert parse_date_from_text("yesterday") == (today - timedelta(days=1)).isoformat()
    assert parse_date_from_text("kal") == (today - timedelta(days=1)).isoformat()
    assert parse_date_from_text("3 days ago") == (today - timedelta(days=3)).isoformat()

    # Short numeric
    assert parse_date_from_text("25/10") == f"{y:04d}-10-25"

    # None when no date
    assert parse_date_from_text("Mera naam Rahul hai") is None


@pytest.mark.asyncio
async def test_targeted_brand_extraction_in_node_parse():
    from saarthi.agent.nodes import node_parse
    from saarthi.agent.llm_router import llm_router

    # Force Tier 3 fallback
    llm_router.openrouter_key = None
    llm_router.gemini_key = None
    llm_router.groq_key = None

    state = {
        "clarification_target_field": "brand",
        "sanitized_transcript": "Brand name is Boat",
    }
    updates = await node_parse(state)
    assert updates.get("pending_confirmation_value") == "Boat" or updates.get("brand_raw") == "Boat"
