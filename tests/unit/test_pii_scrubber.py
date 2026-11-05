import pytest
from consumerdost.security.pii_scrubber import scrub_sensitive_pii


def test_scrub_card_number():
    raw = "My card number is 4111 2222 3333 4444 please check"
    sanitized = scrub_sensitive_pii(raw)
    assert "[REDACTED_CARD]" in sanitized
    assert "4111" not in sanitized


def test_scrub_pin_and_cvv():
    raw = "My PIN is 1234 and my CVV: 889 on the back"
    sanitized = scrub_sensitive_pii(raw)
    assert "[REDACTED_SECRET]" in sanitized
    assert "1234" not in sanitized
    assert "889" not in sanitized


def test_scrub_govt_id():
    raw = "Aadhaar number 1234 5678 9012 submitted"
    sanitized = scrub_sensitive_pii(raw)
    assert "[REDACTED_GOVT_ID]" in sanitized
    assert "1234 5678 9012" not in sanitized


def test_preserve_order_id_and_utr():
    raw = "My Order ID is OD123456789 and UTR: 123456789012 from SBI"
    sanitized = scrub_sensitive_pii(raw)
    assert "OD123456789" in sanitized
    assert "123456789012" in sanitized
