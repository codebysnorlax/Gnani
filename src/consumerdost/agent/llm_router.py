import json
import logging
from consumerdost.config import settings
from consumerdost.domain.models import DisputeCaseDraft
from consumerdost.agent.regex_fallback import extract_entities_regex
from consumerdost.agent.prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

GOLDEN_FIXTURES: list[dict] = [
    {
        "keywords": ["flipkart", "14999", "toota", "phone"],
        "draft": DisputeCaseDraft(
            brand_raw="Flipkart Internet Private Limited",
            category="E_COMMERCE",
            issue_type="ECOMMERCE_DEFECTIVE_GOODS",
            product_name="Smartphone",
            order_id="OD3091823901",
            incident_date="2026-10-25",
            amount_paid_inr=14999.00,
            incident_summary="Smartphone delivered with broken screen on 25 Oct 2026; Flipkart support refused return and refund.",
        ),
    },
    {
        "keywords": ["upi", "1200", "recharge", "utr"],
        "draft": DisputeCaseDraft(
            brand_raw="PhonePe",
            category="FINTECH_UPI",
            issue_type="UPI_FAILED_DEBIT_STUCK",
            product_name="UPI Bill Recharge",
            order_id="123456789012",
            incident_date="2026-10-28",
            amount_paid_inr=1200.00,
            incident_summary="UPI payment debited from bank account on 28 Oct 2026 but recharge transaction failed and funds were not reversed within T+1 window.",
        ),
    },
]


class LLMRouter:
    def __init__(self):
        self.gemini_key = settings.gemini_api_key
        self.groq_key = settings.groq_api_key
        self.openrouter_key = settings.openrouter_api_key

    async def extract_dispute_facts(self, user_text: str) -> tuple[DisputeCaseDraft, int]:
        """Cascading 4-tier fact extractor.
        
        Returns tuple of (DisputeCaseDraft, tier_used).
        Tiers:
          1: Cloud Free LLM (Gemini / Groq)
          2: Secondary Cloud Router (OpenRouter)
          3: Golden Demo Fixture
          4: Pure-Python Regex Catch-All
        """
        lower = user_text.lower()

        # Tier 1: Primary Cloud LLM
        if self.gemini_key:
            try:
                from google import genai
                client = genai.Client(api_key=self.gemini_key)
                response = client.models.generate_content(
                    model=settings.llm_model,
                    contents=f"{EXTRACTION_SYSTEM_PROMPT}\n\nUSER COMPLAINT:\n{user_text}",
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.strip("`").replace("json\n", "")
                data = json.loads(text)
                draft = DisputeCaseDraft(**data)
                draft.check_missing_fields()
                return draft, 1
            except Exception as e:
                logger.warning(f"Tier 1 Gemini LLM call failed: {e}")

        if self.groq_key:
            try:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=self.groq_key)
                completion = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": user_text},
                    ],
                    response_format={"type": "json_object"},
                    timeout=5.0,
                )
                content = completion.choices[0].message.content
                data = json.loads(content)
                draft = DisputeCaseDraft(**data)
                draft.check_missing_fields()
                return draft, 1
            except Exception as e:
                logger.warning(f"Tier 1 Groq LLM call failed: {e}")

        # Tier 2: Secondary Router (OpenRouter)
        if self.openrouter_key:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as http_client:
                    res = await http_client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {self.openrouter_key}"},
                        json={
                            "model": "meta-llama/llama-3.3-70b-instruct:free",
                            "messages": [
                                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                                {"role": "user", "content": user_text},
                            ],
                        },
                    )
                    if res.status_code == 200:
                        content = res.json()["choices"][0]["message"]["content"]
                        if content.startswith("```"):
                            content = content.strip("`").replace("json\n", "")
                        data = json.loads(content)
                        draft = DisputeCaseDraft(**data)
                        draft.check_missing_fields()
                        return draft, 2
            except Exception as e:
                logger.warning(f"Tier 2 OpenRouter call failed: {e}")

        # Tier 3: Golden Demo Fixture
        if settings.demo_mode:
            for fix in GOLDEN_FIXTURES:
                if all(k in lower for k in fix["keywords"]):
                    logger.info("Tier 3: Golden Demo Fixture matched successfully")
                    draft = fix["draft"].model_copy(deep=True)
                    draft.check_missing_fields()
                    return draft, 3

        # Tier 4: Pure-Python Regex Catch-All
        logger.info("Tier 4: Using deterministic pure-python regex fallback")
        draft = extract_entities_regex(user_text)
        return draft, 4


llm_router = LLMRouter()
