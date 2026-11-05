from consumerdost.domain.statutes import STATUTE_REGISTRY, get_statute_entry


def test_ecommerce_defective_goods_mapping():
    entry = get_statute_entry("ECOMMERCE_DEFECTIVE_GOODS")
    assert any("2(10)" in s for s in entry.cpa_sections)
    assert any("2(47)" in s for s in entry.cpa_sections)
    assert any("E-Commerce" in r for r in entry.sectoral_rules)


def test_upi_statute_mapping():
    entry = get_statute_entry("UPI_FAILED_DEBIT_STUCK")
    assert any("2(11)" in s for s in entry.cpa_sections)
    assert any("RBI" in r for r in entry.sectoral_rules)


def test_airline_statute_mapping():
    entry = get_statute_entry("AIRLINE_CANCELLED_OR_DELAYED")
    assert any("DGCA" in r for r in entry.sectoral_rules)


def test_fallback_statute_mapping():
    entry = get_statute_entry("UNKNOWN_CUSTOM_ISSUE")
    assert len(entry.cpa_sections) > 0
    assert "Section 35" in entry.statutory_warning
