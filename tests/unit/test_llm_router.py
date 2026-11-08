import pytest
from saarthi.agent.llm_router import LLMRouter


@pytest.mark.asyncio
async def test_llm_router_regex_fallback_tier_3():
    router = LLMRouter()
    # Explicitly verify Tier 3 when no API keys are present
    router.gemini_key = ""
    router.groq_key = ""
    router.openrouter_key = ""
    text = "Bhaiya Flipkart se 14999 ka phone toota hua mila"
    draft, tier = await router.extract_dispute_facts(text)

    assert tier == 3
    assert draft.amount_paid_inr == 14999.0
    assert "Flipkart" in (draft.brand_raw or "")


@pytest.mark.asyncio
async def test_llm_router_airline_extraction_tier_3():
    router = LLMRouter()
    router.gemini_key = ""
    router.groq_key = ""
    router.openrouter_key = ""
    text = "Indigo flight cancelled on 2026-11-01, amount Rs 7200, PNR 654321."
    draft, tier = await router.extract_dispute_facts(text)

    assert tier == 3
    assert draft.amount_paid_inr == 7200.0
    assert draft.category == "AIRLINES"
