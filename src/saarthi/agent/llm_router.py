import json
import logging
import re
from typing import Any
import inspect

from saarthi.config import settings
from saarthi.domain.models import DisputeCaseDraft
from saarthi.agent.regex_fallback import extract_entities_regex
from saarthi.agent.prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def _notify_progress(cb: Any, text: str) -> None:
    if not cb:
        return
    try:
        if inspect.iscoroutinefunction(cb):
            await cb(text)
        elif callable(cb):
            res = cb(text)
            if inspect.isawaitable(res):
                await res
    except Exception:
        pass


NEURONS_NANO_FREE_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]

MODEL_DISPLAY_NAMES = {
    "nvidia/nemotron-3.5-super-vl:free": "Nemotron 3.5 Super VL",
    "cohere/north-mini-code:free": "North Mini Code",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "Nemotron 3 Nano Omni 30B",
}


def get_candidate_models(preferred_model: str | None = None) -> list[str]:
    """Return ordered list of OpenRouter free models with auto-fallback."""
    candidates = []
    if preferred_model and preferred_model != "auto":
        candidates.append(preferred_model)
    elif settings.openrouter_model and settings.openrouter_model != "auto":
        candidates.append(settings.openrouter_model)

    for m in NEURONS_NANO_FREE_MODELS:
        if m not in candidates:
            candidates.append(m)
    return candidates


class LLMRouter:
    def __init__(self):
        self.gemini_key = settings.gemini_api_key
        self.groq_key = settings.groq_api_key
        self.openrouter_key = settings.openrouter_api_key
        self.last_engine: str = "Standard Engine"

    async def extract_dispute_facts(
        self,
        user_text: str,
        progress_callback: Any = None,
        preferred_model: str | None = None,
    ) -> tuple[DisputeCaseDraft, int]:
        """Cascading fact extractor.
        
        Returns tuple of (DisputeCaseDraft, tier_used).
        Tiers:
          1: OpenRouter Free Models (Neurons Nano)
          2: Google Gemini Flash-Lite / Groq (Neurons Mini)
          3: Pure-Python Deterministic Regex Catch-All (Standard Engine)
        """
        lower = user_text.lower()

        # Tier 1: Neurons Nano (OpenRouter Free Models)
        if self.openrouter_key:
            import httpx
            models_to_try = get_candidate_models(preferred_model)
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "HTTP-Referer": "https://github.com/codebysnorlax/Saarthi",
                "X-Title": "SAARTHI Consumer Grievance Assistant",
            }
            for model_name in models_to_try:
                display = MODEL_DISPLAY_NAMES.get(model_name, model_name.split("/")[-1].replace(":free", ""))
                await _notify_progress(progress_callback, f"Connecting to Neurons Nano ({display})...")
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
                            self.last_engine = f"Neurons Nano ({display})"
                            await _notify_progress(progress_callback, f"Connected to Neurons Nano ({display})\nThinking...")
                            return draft, 1
                        else:
                            logger.warning(f"Tier 1 OpenRouter call failed for {model_name} with status {res.status_code}")
                except Exception as e:
                    logger.warning(f"Tier 1 OpenRouter call failed for {model_name}: {e}")

        # Tier 2: Neurons Mini (Google Gemini API / Groq)
        if self.gemini_key:
            await _notify_progress(progress_callback, "Could not connect to Neurons Nano. Connecting to Neurons Mini...")

            try:
                from google import genai
                from google.genai import types
                client = genai.Client(
                    api_key=self.gemini_key,
                    http_options=types.HttpOptions(timeout=10000),
                )
                gemini_models = [
                    settings.llm_model,
                    "gemini-3.5-flash-lite",
                    "gemini-3.1-flash-lite",
                    "gemini-flash-lite-latest",
                    "gemini-3.8-flash",
                ]
                seen_gemini = set()
                for gem_model in gemini_models:
                    if not gem_model or gem_model in seen_gemini:
                        continue
                    seen_gemini.add(gem_model)
                    try:
                        response = await client.aio.models.generate_content(
                            model=gem_model,
                            contents=f"{EXTRACTION_SYSTEM_PROMPT}\n\nUSER COMPLAINT:\n{user_text}",
                        )
                        text = response.text.strip()
                        if text.startswith("```"):
                            text = re.sub(r"^```(?:json)?\n", "", text)
                            text = re.sub(r"\n```$", "", text)
                        data = json.loads(text)
                        draft = DisputeCaseDraft(**data)
                        draft.check_missing_fields()
                        self.last_engine = "Neurons Mini"
                        await _notify_progress(progress_callback, "Connected to Neurons Mini\nThinking...")
                        return draft, 2
                    except Exception as ge:
                        logger.warning(f"Tier 2 Gemini model {gem_model} failed: {ge}")
            except Exception as e:
                logger.warning(f"Tier 2 Gemini LLM call failed: {e}")

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
                self.last_engine = "Neurons Mini"
                await _notify_progress(progress_callback, "Connected to Neurons Mini\nThinking...")
                return draft, 2
            except Exception as e:
                logger.warning(f"Tier 2 Groq LLM call failed: {e}")

        # Tier 3: Pure-Python Deterministic Regex Catch-All
        await _notify_progress(progress_callback, "Could not connect to Neurons. Using standard engine...")
        self.last_engine = "Standard Engine"
        logger.info("Tier 3: Using deterministic pure-python regex fallback")
        draft = extract_entities_regex(user_text)
        return draft, 3


llm_router = LLMRouter()
