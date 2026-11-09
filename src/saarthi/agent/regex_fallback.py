import re
from datetime import date, timedelta
from saarthi.domain.models import DisputeCaseDraft
from saarthi.domain.brands import brand_directory


AMOUNT_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)\s*(?:₹|rs\.?|inr|rupees|rupaye|ka\b|/-)",
    re.IGNORECASE,
)

EXPLICIT_ORDER_PATTERN = re.compile(
    r"(?:order|utr|pnr|txn|transaction|reference|ref)(?:\s*(?:id|no|number|code))?\s*(?:is|hai|tha)?\s*[:#\-_]?\s*([A-Z0-9_-]{6,30})",
    re.IGNORECASE,
)

FALLBACK_ORDER_PATTERN = re.compile(
    r"\b(OD\d{8,25}|\d{12})\b"
)

DATE_PATTERN = re.compile(
    r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b|\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"
)

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_date_from_text(text: str) -> str | None:
    """Robust deterministic parser for conversational dates, ordinals, and relative tokens."""
    if not text:
        return None

    lower_text = text.lower()
    today = date.today()

    # 1. Relative phrases
    if "kal" in lower_text or "yesterday" in lower_text or "beeta kal" in lower_text:
        return (today - timedelta(days=1)).isoformat()
    if "aaj" in lower_text or "today" in lower_text:
        return today.isoformat()
    if "parson" in lower_text or "parso" in lower_text:
        return (today - timedelta(days=2)).isoformat()

    days_ago_match = re.search(r"\b(\d{1,2})\s+(?:days?|din)\s+(?:ago|pehle)\b", lower_text)
    if days_ago_match:
        n_days = int(days_ago_match.group(1))
        return (today - timedelta(days=n_days)).isoformat()

    # 2. Standard numeric formats (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD, YYYY/MM/DD)
    d_match = re.search(
        r"\b(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})\b|\b(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})\b",
        text,
    )
    if d_match:
        if d_match.group(1) and d_match.group(3):
            d, m, y = int(d_match.group(1)), int(d_match.group(2)), int(d_match.group(3))
            try:
                return f"{y:04d}-{m:02d}-{d:02d}"
            except Exception:
                pass
        elif d_match.group(4):
            y, m, d = int(d_match.group(4)), int(d_match.group(5)), int(d_match.group(6))
            try:
                return f"{y:04d}-{m:02d}-{d:02d}"
            except Exception:
                pass

    # 3. Verbal Day-First: e.g. "25th October 2026", "25 Oct", "25th oct"
    day_first = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)(?:\s+(\d{2,4}))?\b", text)
    if day_first:
        day_num = int(day_first.group(1))
        month_word = day_first.group(2).lower()
        if month_word in MONTH_MAP:
            m_num = MONTH_MAP[month_word]
            y_str = day_first.group(3)
            if y_str:
                year_num = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
            else:
                year_num = today.year
            try:
                return f"{year_num:04d}-{m_num:02d}-{day_num:02d}"
            except Exception:
                pass

    # 4. Verbal Month-First: e.g. "October 25th, 2026", "Oct 25"
    month_first = re.search(r"\b([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{2,4}))?\b", text)
    if month_first:
        month_word = month_first.group(1).lower()
        if month_word in MONTH_MAP:
            m_num = MONTH_MAP[month_word]
            day_num = int(month_first.group(2))
            y_str = month_first.group(3)
            if y_str:
                year_num = int(y_str) if len(y_str) == 4 else 2000 + int(y_str)
            else:
                year_num = today.year
            try:
                return f"{year_num:04d}-{m_num:02d}-{day_num:02d}"
            except Exception:
                pass

    # 5. Short numeric DD/MM or DD-MM (e.g. "25/10")
    short_d = re.search(r"\b(\d{1,2})[-/](\d{1,2})\b", text)
    if short_d:
        d, m = int(short_d.group(1)), int(short_d.group(2))
        if 1 <= d <= 31 and 1 <= m <= 12:
            return f"{today.year:04d}-{m:02d}-{d:02d}"

    return None


def extract_entities_regex(text: str) -> DisputeCaseDraft:
    """Deterministic, pure-Python regex and keyword fact extractor.
    
    Zero-API dependency. Used as Tier 4 catch-all during API outages.
    """
    if not text:
        return DisputeCaseDraft()

    lower_text = text.lower()

    # 1. Extract Amount
    amount = None
    amt_match = AMOUNT_PATTERN.search(text)
    if amt_match:
        raw_amt = amt_match.group(1) or amt_match.group(2)
        if raw_amt:
            clean_amt = raw_amt.replace(",", "")
            try:
                amount = float(clean_amt)
            except ValueError:
                pass

    # 2. Extract Brand using brand directory aliases
    detected_brand = None
    category = "E_COMMERCE"
    for alias in brand_directory.all_aliases:
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, lower_text):
            brand_info = brand_directory.alias_to_brand[alias]
            detected_brand = brand_info["corporate_name"]
            category = brand_info.get("category", "E_COMMERCE")
            break

    # 3. Extract Order ID / Transaction ID
    order_id = None
    explicit_match = EXPLICIT_ORDER_PATTERN.search(text)
    if explicit_match:
        order_id = explicit_match.group(1).strip()
    else:
        fallback_match = FALLBACK_ORDER_PATTERN.search(text)
        if fallback_match:
            order_id = fallback_match.group(1).strip()

    # 4. Extract Incident Date
    incident_date_str = parse_date_from_text(text)

    # 5. Extract Category and Issue Type
    issue_type = "ECOMMERCE_REFUND_DELAY_OR_DENIAL"
    if any(k in lower_text for k in ["flight", "airline", "boarding", "cancelled"]):
        category = "AIRLINES"
        issue_type = "AIRLINE_CANCELLED_OR_DELAYED"
    elif any(k in lower_text for k in ["upi", "gpay", "phonepe", "debit", "recharge", "utr"]):
        category = "FINTECH_UPI"
        issue_type = "UPI_FAILED_DEBIT_STUCK"
    elif any(k in lower_text for k in ["toota", "broken", "damaged", "screen", "defect"]):
        category = "E_COMMERCE"
        issue_type = "ECOMMERCE_DEFECTIVE_GOODS"
    elif any(k in lower_text for k in ["expired", "spoiled", "kharaab", "missing item"]):
        category = "QUICK_COMMERCE"
        issue_type = "QCOMM_EXPIRED_OR_MISSING_ITEMS"
    elif any(k in lower_text for k in ["dark pattern", "hidden fee", "extra charge", "forced"]):
        category = "E_COMMERCE"
        issue_type = "DARK_PATTERNS_HIDDEN_FEES"

    # 6. Extract Complainant Full Name & Contact
    full_name = None
    name_match = re.search(
        r"(?:mera\s+naam|my\s+name\s+is|name\s*[:\-])\s+([A-Za-z]{2,25}(?:\s+[A-Za-z]{2,25}){1,3})(?:\s+hai|\s+aur|\.|\,|$)",
        text,
        re.IGNORECASE,
    )
    if name_match:
        full_name = name_match.group(1).strip()
        full_name = re.sub(r"\s+(?:hai|tha)$", "", full_name, flags=re.IGNORECASE).strip()

    contact = None
    email_match = re.search(r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b", text)
    if email_match:
        contact = email_match.group(1).strip()
    else:
        phone_match = re.search(r"\b([6-9]\d{9})\b", text)
        if phone_match:
            contact = phone_match.group(1).strip()

    # 7. Synthesize Formal English Statement of Facts
    brand_display = detected_brand or "the Corporate Vendor"
    amt_display = f"₹{amount:,.2f}" if amount else "the invoiced consideration"
    order_display = f"under Reference/Order ID '{order_id}'" if order_id else ""
    narrative = (
        f"On or about {incident_date_str}, the Complainant purchased goods/services from {brand_display} "
        f"{order_display} for {amt_display}. The transaction resulted in {issue_type.replace('_', ' ').title()}. "
        f"Despite formal requests for rectification, the corporate entity failed to provide statutory redressal."
    )

    draft = DisputeCaseDraft(
        brand_raw=detected_brand,
        category=category,
        issue_type=issue_type,
        amount_paid_inr=amount,
        incident_date=incident_date_str,
        order_id=order_id,
        complainant_full_name=full_name,
        complainant_contact=contact,
        incident_summary=narrative,
    )
    draft.check_missing_fields()
    return draft

