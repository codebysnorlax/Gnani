import json
import logging
from saarthi.config import settings
from saarthi.domain.models import DisputeCaseDraft
from saarthi.agent.regex_fallback import extract_entities_regex
from saarthi.agent.prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self):
        self.gemini_key = settings.gemini_api_key
        self.groq_key = settings.groq_api_key
        self.openrouter_key = settings.openrouter_api_key

    async def extract_dispute_facts(self, user_text: str) -> tuple[DisputeCaseDraft, int]:
        """Cascading fact extractor.
        
        Returns tuple of (DisputeCaseDraft, tier_used).
        Tiers:
          1: Cloud Free LLM (Gemini / Groq)
          2: Secondary Cloud Router (OpenRouter)
          3: Pure-Python Deterministic Regex Catch-All
        """
        lower = user_text.lower()

        # Tier 1: Primary Cloud LLM
        if self.gemini_key:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(
                    api_key=self.gemini_key,
                    http_options=types.HttpOptions(timeout=10000),
                )
                response = await client.aio.models.generate_content(
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

        # Tier 2: Secondary Router (OpenRouter Free Models)
        if self.openrouter_key:
            import httpx
            models_to_try = [
                "google/gemma-4-31b-it:free",
                "nvidia/nemotron-3.5-lightning:free",
                "liquid/lfm-2.5-2.6b:free",
            ]
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "HTTP-Referer": "https://github.com/codebysnorlax/Saarthi",
                "X-Title": "SAARTHI Consumer Grievance Assistant",
            }
            for model_name in models_to_try:
                try:
                    async with httpx.AsyncClient(timeout=6.0) as http_client:
                        res = await http_client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers=headers,
                            json={
                                "model": model_name,
                                "messages": [
                                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                                    {"role": "user", "content": user_text},
                                ],
                                "temperature": 0.1,
                            },
                        )
                        if res.status_code == 200:
                            content = res.json()["choices"][0]["message"]["content"].strip()
                            if content.startswith("```"):
                                content = re.sub(r"^```(?:json)?\n", "", content)
                                content = re.sub(r"\n```$", "", content)
                            data = json.loads(content)
                            draft = DisputeCaseDraft(**data)
                            draft.check_missing_fields()
                            return draft, 2
                except Exception as e:
                    logger.warning(f"Tier 2 OpenRouter call failed for {model_name}: {e}")

        # Tier 3: Pure-Python Regex Catch-All
        logger.info("Tier 3: Using deterministic pure-python regex fallback")
        draft = extract_entities_regex(user_text)
        return draft, 3


llm_router = LLMRouter()
