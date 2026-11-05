import re

# Regex patterns for sensitive PII
CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){16}\b")
SECRET_PATTERN = re.compile(
    r"\b(?:pin|cvv|cvc|otp|password|pwd)\s*(?:is|:|=|-)?\s*([0-9]{3,6})\b",
    re.IGNORECASE,
)
# Match 12-digit number groups (like Aadhaar: 1234 5678 9012 or 1234-5678-9012 or 123456789012)
TWELVE_DIGIT_PATTERN = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
TXN_PREFIX_PATTERN = re.compile(
    r"(?:utr|order|ref|txn|transaction|id)\s*[:#\-_]?\s*$",
    re.IGNORECASE,
)


def scrub_sensitive_pii(text: str) -> str:
    """Deterministic regex sanitizer that redacts payment cards, secrets, and govt IDs.
    
    Preserves legitimate order numbers, PNRs, and UPI UTR references.
    """
    if not text:
        return ""

    # Redact 16-digit card numbers
    sanitized = CARD_PATTERN.sub("[REDACTED_CARD]", text)

    # Redact explicit PIN/CVV/OTP disclosures
    def mask_secret(match: re.Match) -> str:
        full_match = match.group(0)
        secret_digits = match.group(1)
        return full_match.replace(secret_digits, "[REDACTED_SECRET]")

    sanitized = SECRET_PATTERN.sub(mask_secret, sanitized)

    # Redact 12-digit numbers unless preceded by transaction/order keyword prefix
    def mask_govt_id(match: re.Match) -> str:
        start_pos = match.start()
        # Look at the text leading up to this match (up to 30 chars prior)
        preceding_text = sanitized[max(0, start_pos - 30):start_pos].strip()
        if TXN_PREFIX_PATTERN.search(preceding_text):
            # It's an order or UTR number; keep it
            return match.group(0)
        return "[REDACTED_GOVT_ID]"

    sanitized = TWELVE_DIGIT_PATTERN.sub(mask_govt_id, sanitized)

    return sanitized
