from __future__ import annotations

from datetime import date
from src.consumerdost.agent.extractor import deterministic_offline_extract


def test_ecommerce_defective_goods_extraction():
    sample = "Bhaiya maine Flipkart se 14,999 ka phone mangaya tha. Box khola toh screen tooti hui thi. Order ID OD3091823901 hai. Refund reject kar diya."
    res = deterministic_offline_extract(sample, today=date(2026, 11, 3))
    assert res.brand_raw == "Flipkart"
    assert res.category == "E_COMMERCE"
    assert res.issue_type == "ECOMMERCE_DEFECTIVE_GOODS"
    assert res.amount_paid_inr == 14999.0
    assert res.order_id == "OD3091823901"
    assert "Flipkart" in res.incident_summary_en
    assert "14,999.00" in res.incident_summary_en


def test_upi_failed_debit_extraction():
    sample = "Mera 1200 rupees ka UPI payment GPay pe atka hua hai 5 din se. UTR 429102918231. Bank se debit ho gaya."
    res = deterministic_offline_extract(sample, today=date(2026, 11, 3))
    assert res.brand_raw == "Google Pay"
    assert res.category == "FINTECH_PAYMENTS"
    assert res.issue_type == "UPI_FAILED_DEBIT_STUCK"
    assert res.amount_paid_inr == 1200.0
    assert res.order_id == "429102918231"


def test_airline_cancellation_relative_date():
    sample = "IndiGo flight got cancelled yesterday, airline is refusing refund."
    res = deterministic_offline_extract(sample, today=date(2026, 11, 3))
    assert res.brand_raw == "IndiGo"
    assert res.category == "AIRLINES_TRAVEL"
    assert res.issue_type == "AIRLINE_CANCELLED_OR_DELAYED"
    assert res.incident_date == "2026-11-02"


def test_missing_order_id_triggers_none():
    sample = "Swiggy se khana mangaya tha kharab khana aaya aur delivery boy sun nahi raha."
    res = deterministic_offline_extract(sample, today=date(2026, 11, 3))
    assert res.brand_raw == "Swiggy"
    assert res.category == "QUICK_COMMERCE_FOOD"
    assert res.order_id is None
