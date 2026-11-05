from datetime import date, timedelta
from consumerdost.domain.calculator import calculate_claim, format_inr


def test_standard_claim_calculation():
    incident = date(2026, 10, 25)
    notice = date(2026, 11, 3)  # 9 days elapsed
    breakdown = calculate_claim(
        amount_paid_inr=14999.00,
        incident_date=incident,
        notice_date=notice,
        issue_type="ECOMMERCE_DEFECTIVE_GOODS",
    )

    assert breakdown.principal_paise == 1499900
    assert breakdown.days_elapsed == 9
    assert breakdown.damages_paise == 500000  # ₹5,000 tier for ₹14,999
    assert breakdown.statutory_penalty_paise == 0
    # Interest: 1499900 * 0.09 * 9 / 365 = 3328.545 -> 3329 paise
    assert breakdown.interest_paise == 3329
    assert breakdown.total_demanded_paise == 1499900 + 3329 + 500000


def test_upi_penalty_calculation():
    incident = date.today() - timedelta(days=6)
    breakdown = calculate_claim(
        amount_paid_inr=1200.00,
        incident_date=incident,
        issue_type="UPI_FAILED_DEBIT_STUCK",
    )
    # 6 days elapsed -> 5 days after T+1 -> 5 * ₹100 = ₹500 (50000 paise)
    assert breakdown.statutory_penalty_paise == 50000
    assert breakdown.damages_paise == 150000  # ₹1,500 tier for ₹1,200


def test_airline_penalty_calculation():
    incident = date.today() - timedelta(days=2)
    breakdown = calculate_claim(
        amount_paid_inr=6500.00,
        incident_date=incident,
        issue_type="AIRLINE_CANCELLED_OR_DELAYED",
    )
    assert breakdown.statutory_penalty_paise == 500000  # DGCA ₹5,000 baseline


def test_inr_formatting():
    assert format_inr(14999.00) == "₹14,999.00"
    assert format_inr(20032.28) == "₹20,032.28"
    assert format_inr(100000.50) == "₹1,00,000.50"
