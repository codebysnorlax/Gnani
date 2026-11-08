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


def test_unknown_brand_fallback():
    brand = resolve_brand(
        "Sharma Electronics",
        fallback_if_unknown=True,
        custom_email="support@sharma.in",
        custom_address="12 MG Road, Bengaluru",
    )
    assert brand is not None
    assert brand["canonical_name"] == "SHARMA ELECTRONICS"
    assert brand["nodal_email"] == "support@sharma.in"
    assert brand["registered_address"] == "12 MG Road, Bengaluru"
    assert brand["nodal_officer_name"] == "Nodal Grievance Officer"


def test_create_fallback_brand_default():
    from consumerdost.domain.brands import create_fallback_brand
    fallback = create_fallback_brand("Local Store")
    assert fallback["canonical_name"] == "LOCAL STORE"
    assert "grievance@localstore.com" in fallback["nodal_email"]
    assert fallback["registered_address"] == "Registered Office, India"
