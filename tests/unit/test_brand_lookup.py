from consumerdost.domain.brands import resolve_brand


def test_exact_brand_match():
    brand = resolve_brand("Flipkart")
    assert brand is not None
    assert brand["canonical_name"] == "FLIPKART"
    assert "grievance.officer@flipkart.com" in brand["nodal_email"]
    assert brand["twitter_handle"] == "@FlipkartSupport"


def test_alias_brand_match():
    brand = resolve_brand("amazon india")
    assert brand is not None
    assert brand["canonical_name"] == "AMAZON"


def test_fuzzy_brand_match():
    brand = resolve_brand("flpkart", threshold=80.0)
    assert brand is not None
    assert brand["canonical_name"] == "FLIPKART"


def test_unknown_brand():
    brand = resolve_brand("RandomKiranaStore12345")
    assert brand is None
