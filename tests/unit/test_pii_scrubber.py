import pytest
from saarthi.security.pii_scrubber import scrub_sensitive_pii


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


def test_preserve_conversational_utr():
    assert "123456789012" in scrub_sensitive_pii("my utr is 123456789012")
    assert "987654321098" in scrub_sensitive_pii("UTR number 987654321098 bank debit")
    assert "555544443333" in scrub_sensitive_pii("Transaction reference 555544443333")


def test_preserve_standalone_utr_with_target_field():
    raw = "123456789012"
    # When target field is order_id, standalone 12 digits is preserved
    assert scrub_sensitive_pii(raw, target_field="order_id") == "123456789012"
    # Without target field and without transaction prefix, standalone 12 digits is scrubbed
    assert scrub_sensitive_pii(raw) == "[REDACTED_GOVT_ID]"
