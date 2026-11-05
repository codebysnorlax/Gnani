from consumerdost.agent.regex_fallback import extract_entities_regex


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
