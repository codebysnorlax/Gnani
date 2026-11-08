"""Synthetic test fixtures isolated for automated testing purposes only.

These fixtures MUST NOT be imported or referenced by production runtime code.
"""

from saarthi.domain.models import DisputeCaseDraft

SYNTHETIC_TEST_FIXTURES: list[dict] = [
    {
        "keywords": ["flipkart", "14999", "phone"],
        "draft": DisputeCaseDraft(
            brand_raw="Flipkart Internet Private Limited",
            category="E_COMMERCE",
            issue_type="ECOMMERCE_DEFECTIVE_GOODS",
            product_name="Smartphone",
            order_id="OD3091823901",
            incident_date="2026-10-25",
            amount_paid_inr=14999.00,
            complainant_full_name="Rohan Sharma",
            complainant_contact="rohan@example.com",
            incident_summary="Smartphone delivered with broken screen on 25 Oct 2026; Flipkart support refused return and refund.",
        ),
    },
    {
        "keywords": ["upi", "1200", "recharge"],
        "draft": DisputeCaseDraft(
            brand_raw="PhonePe",
            category="FINTECH_UPI",
            issue_type="UPI_FAILED_DEBIT_STUCK",
            product_name="UPI Bill Recharge",
            order_id="123456789012",
            incident_date="2026-10-28",
            amount_paid_inr=1200.00,
            complainant_full_name="Sunita Devi",
            complainant_contact="9876543210",
            incident_summary="UPI payment debited from bank account on 28 Oct 2026 but recharge transaction failed and funds were not reversed within T+1 window.",
        ),
    },
    {
        "keywords": ["indigo", "6500"],
        "draft": DisputeCaseDraft(
            brand_raw="InterGlobe Aviation Limited (IndiGo)",
            category="AIRLINE_TRAVEL",
            issue_type="AIRLINE_CANCELLATION_REFUND",
            product_name="Flight Ticket 6E-204",
            order_id="98765432",
            incident_date="2026-11-01",
            amount_paid_inr=6500.00,
            complainant_full_name="Vikram Seth",
            complainant_contact="vikram@example.com",
            incident_summary="IndiGo flight 6E-204 was cancelled without mandatory statutory notice; ticket refund was denied contrary to DGCA CAR regulations.",
        ),
    },
]
