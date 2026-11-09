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


@pytest.mark.asyncio
async def test_llm_router_openrouter_circuit_breaker_on_503():
    from unittest.mock import MagicMock, patch

    router = LLMRouter()
    router.openrouter_key = "test-sk-invalid"
    router.gemini_key = ""
    router.groq_key = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 503

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        draft, tier = await router.extract_dispute_facts("Flipkart order Rs 5000")

    # Halts after first model failure instead of trying all candidate models
    assert call_count == 1
    assert tier == 3
    assert draft.amount_paid_inr == 5000.0


@pytest.mark.asyncio
async def test_llm_router_openrouter_circuit_breaker_on_401():
    from unittest.mock import MagicMock, patch

    router = LLMRouter()
    router.openrouter_key = "test-sk-invalid"
    router.gemini_key = ""
    router.groq_key = ""

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_resp

    with patch("httpx.AsyncClient.post", side_effect=mock_post):
        draft, tier = await router.extract_dispute_facts("Amazon order Rs 2999")

    assert call_count == 1
    assert tier == 3
    assert draft.amount_paid_inr == 2999.0

