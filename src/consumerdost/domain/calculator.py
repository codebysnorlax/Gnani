from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import NamedTuple


class ClaimBreakdown(NamedTuple):
    principal_paise: int
    interest_paise: int
    statutory_penalty_paise: int
    damages_paise: int
    total_demanded_paise: int
    days_elapsed: int

    @property
    def principal_inr(self) -> float:
        return self.principal_paise / 100.0

    @property
    def interest_inr(self) -> float:
        return self.interest_paise / 100.0

    @property
    def statutory_penalty_inr(self) -> float:
        return self.statutory_penalty_paise / 100.0

    @property
    def damages_inr(self) -> float:
        return self.damages_paise / 100.0

    @property
    def total_demanded_inr(self) -> float:
        return self.total_demanded_paise / 100.0

    @property
    def illustrative_total_demand_inr(self) -> float:
        """Illustrative pre-litigation demand estimate in INR (indicative discussion estimate, not legal advice)."""
        return self.total_demanded_paise / 100.0


def format_inr(amount_inr: float | Decimal) -> str:
    """Format an INR amount into standard Indian currency string (e.g. ₹14,999.00)."""
    val = float(amount_inr)
    # Format with 2 decimal places
    s = f"{val:.2f}"
    parts = s.split(".")
    int_part, dec_part = parts[0], parts[1]

    # Indian number formatting: last 3 digits, then groups of 2
    if len(int_part) > 3:
        last3 = int_part[-3:]
        remaining = int_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        int_part = ",".join(groups) + "," + last3

    return f"₹{int_part}.{dec_part}"


def calculate_claim(
    amount_paid_inr: float | Decimal,
    incident_date: date | str,
    notice_date: date | None = None,
    issue_type: str | None = None,
) -> ClaimBreakdown:
    """Deterministically compute claim in integer paise with 9% p.a. interest, statutory penalties, and tiered damages."""
    if isinstance(incident_date, str):
        incident_date = date.fromisoformat(incident_date)
    if notice_date is None:
        notice_date = date.today()

    days_elapsed = max(1, (notice_date - incident_date).days)

    # 1. Principal paise
    dec_amount = Decimal(str(amount_paid_inr))
    principal_paise = int((dec_amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    # 2. Equitable Interest: 9% p.a.
    interest_calc = (
        Decimal(principal_paise)
        * Decimal("0.09")
        * Decimal(days_elapsed)
        / Decimal("365")
    )
    interest_paise = int(interest_calc.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    # 3. Sectoral Statutory Penalty
    issue_type_upper = (issue_type or "").upper()
    if issue_type_upper == "UPI_FAILED_DEBIT_STUCK":
        # RBI T+1 rule: ₹100/day after T+1
        days_beyond_t1 = max(0, days_elapsed - 1)
        statutory_penalty_paise = days_beyond_t1 * 10000  # ₹100 = 10000 paise
    elif issue_type_upper == "AIRLINE_CANCELLED_OR_DELAYED":
        # DGCA baseline compensation slab ₹5,000
        statutory_penalty_paise = 500000
    else:
        statutory_penalty_paise = 0

    # 4. Tiered Harassment & Mental Agony Damages
    # Principal < ₹500 -> ₹500 (50000 paise)
    # Principal ₹500 to ₹4,999.99 -> ₹1,500 (150000 paise)
    # Principal ₹5,000 to ₹24,999.99 -> ₹5,000 (500000 paise)
    # Principal >= ₹25,000 -> ₹10,000 (1000000 paise)
    if principal_paise < 50000:
        damages_paise = 50000
    elif principal_paise < 500000:
        damages_paise = 150000
    elif principal_paise < 2500000:
        damages_paise = 500000
    else:
        damages_paise = 1000000

    total_demanded_paise = (
        principal_paise + interest_paise + statutory_penalty_paise + damages_paise
    )

    return ClaimBreakdown(
        principal_paise=principal_paise,
        interest_paise=interest_paise,
        statutory_penalty_paise=statutory_penalty_paise,
        damages_paise=damages_paise,
        total_demanded_paise=total_demanded_paise,
        days_elapsed=days_elapsed,
    )
