import pytest
from consumerdost.agent.llm_router import LLMRouter


@pytest.mark.asyncio
async def test_llm_router_fixture_match_tier_3():
    router = LLMRouter()
    # No API keys configured -> falls back to Tier 3 or Tier 4
    text = "Bhaiya Flipkart se 14999 ka phone toota hua mila"
    draft, tier = await router.extract_dispute_facts(text)

    assert tier in (3, 4)
    assert draft.amount_paid_inr == 14999.0
    assert "Flipkart" in (draft.brand_raw or "")


@pytest.mark.asyncio
async def test_llm_router_regex_fallback_tier_4():
    router = LLMRouter()
    text = "Indigo flight cancelled on 2026-11-01, amount Rs 7200, PNR 654321."
    draft, tier = await router.extract_dispute_facts(text)

    assert tier in (3, 4)
    assert draft.amount_paid_inr == 7200.0
    assert draft.category == "AIRLINES"
