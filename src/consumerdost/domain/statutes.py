from typing import NamedTuple


class StatuteEntry(NamedTuple):
    cpa_sections: list[str]
    sectoral_rules: list[str]
    relief_demanded: str
    statutory_warning: str


DEFAULT_STATUTORY_WARNING = (
    "Failure to comply with this notice within 7 calendar days will compel "
    "the Complainant to initiate proceedings before the competent District Consumer "
    "Disputes Redressal Commission (DCDRC) under Section 35 of the Consumer Protection Act, 2019, "
    "claiming full refund, accrued interest, statutory compensation, and legal costs."
)

STATUTE_REGISTRY: dict[str, StatuteEntry] = {
    "ECOMMERCE_DEFECTIVE_GOODS": StatuteEntry(
        cpa_sections=[
            "Section 2(10) of CPA 2019 (Defect in Goods)",
            "Section 2(47) of CPA 2019 (Unfair Trade Practice)",
        ],
        sectoral_rules=[
            "Consumer Protection (E-Commerce) Rules, 2020",
            "Sale of Goods Act, 1930 (Section 15 & 16)",
        ],
        relief_demanded="100% Refund + 9% p.a. Interest + Tiered Harassment Damages",
        statutory_warning=DEFAULT_STATUTORY_WARNING,
    ),
    "ECOMMERCE_REFUND_DELAY_OR_DENIAL": StatuteEntry(
        cpa_sections=[
            "Section 2(11) of CPA 2019 (Deficiency in Service)",
            "Section 2(47) of CPA 2019 (Unfair Trade Practice)",
        ],
        sectoral_rules=[
            "Consumer Protection (E-Commerce) Rules, 2020 (Rule 4 & 5 Mandatory Grievance Mechanism)",
        ],
        relief_demanded="Immediate Refund + 9% p.a. Interest + Tiered Harassment Damages",
        statutory_warning=DEFAULT_STATUTORY_WARNING,
    ),
    "QCOMM_EXPIRED_OR_MISSING_ITEMS": StatuteEntry(
        cpa_sections=[
            "Section 2(10) of CPA 2019 (Defect in Goods)",
            "Section 2(11) of CPA 2019 (Deficiency in Service)",
        ],
        sectoral_rules=[
            "Food Safety and Standards Act, 2006",
            "Consumer Protection (E-Commerce) Rules, 2020",
        ],
        relief_demanded="100% Order Refund + Tiered Harassment Damages",
        statutory_warning=DEFAULT_STATUTORY_WARNING,
    ),
    "DARK_PATTERNS_HIDDEN_FEES": StatuteEntry(
        cpa_sections=[
            "Section 2(47) of CPA 2019 (Unfair Trade Practice)",
            "Section 18 of CPA 2019 (CCPA Enforcement Powers)",
        ],
        sectoral_rules=[
            "CCPA Guidelines for Prevention and Regulation of Dark Patterns, 2023",
        ],
        relief_demanded="Immediate Reversal of Drip Pricing / Forced Add-On Charges + Damages",
        statutory_warning=DEFAULT_STATUTORY_WARNING,
    ),
    "UPI_FAILED_DEBIT_STUCK": StatuteEntry(
        cpa_sections=[
            "Section 2(11) of CPA 2019 (Deficiency in Service)",
        ],
        sectoral_rules=[
            "RBI Circular RBI/2019-20/67 (DPSS.CO.PD No.629) on TAT Harmonisation",
        ],
        relief_demanded="Principal Reversal + ₹100/day Mandatory Statutory Penalty beyond T+1 + Damages",
        statutory_warning=DEFAULT_STATUTORY_WARNING,
    ),
    "AIRLINE_CANCELLED_OR_DELAYED": StatuteEntry(
        cpa_sections=[
            "Section 2(11) of CPA 2019 (Deficiency in Service)",
        ],
        sectoral_rules=[
            "DGCA CAR Section 3, Series M, Part IV (Passenger Charter)",
        ],
        relief_demanded="100% Cash Refund + ₹5,000–₹10,000 DGCA Statutory Compensation",
        statutory_warning=DEFAULT_STATUTORY_WARNING,
    ),
    "TELECOM_WRONGFUL_BILLING_OR_VAS": StatuteEntry(
        cpa_sections=[
            "Section 2(11) of CPA 2019 (Deficiency in Service)",
            "Section 2(47) of CPA 2019 (Unfair Trade Practice)",
        ],
        sectoral_rules=[
            "TRAI Quality of Service (QoS) Regulations",
        ],
        relief_demanded="Full Reversal of Unauthorized Charges + Tiered Harassment Damages",
        statutory_warning=DEFAULT_STATUTORY_WARNING,
    ),
}

GENERIC_STATUTE_ENTRY = StatuteEntry(
    cpa_sections=[
        "Section 2(11) of CPA 2019 (Deficiency in Service)",
        "Section 2(47) of CPA 2019 (Unfair Trade Practice)",
    ],
    sectoral_rules=[
        "Consumer Protection Act, 2019",
    ],
    relief_demanded="100% Refund / Reversal + 9% p.a. Interest + Damages",
    statutory_warning=DEFAULT_STATUTORY_WARNING,
)


def get_statute_entry(issue_type: str | None) -> StatuteEntry:
    """Retrieve immutable statute mapping for a given issue type."""
    if not issue_type:
        return GENERIC_STATUTE_ENTRY
    return STATUTE_REGISTRY.get(issue_type.upper(), GENERIC_STATUTE_ENTRY)
