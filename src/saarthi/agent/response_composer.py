"""Dynamic context-aware response composer for SAARTHI consumer grievances.

Grounded strictly in known case facts, avoids repeating answered questions,
eliminates all emoji, and generates structured visible and spoken responses.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from saarthi.config import settings
from saarthi.domain.calculator import format_inr
from saarthi.speech.tags import strip_audio_tags

logger = logging.getLogger(__name__)

# Allowed speech tags for Timbre v3.0 per PRD
ALLOWED_TAGS = {"<pauses>", "<slow>"}
TAG_REGEX = re.compile(r"<([^>]+)>")


@dataclass
class ComposedResponse:
    visible_text: str
    spoken_text: str
    target_field: str


def sanitize_speech_tags(text: str, max_tags: int = 2) -> str:
    """Enforce tag allowlist (<pauses>, <slow>), no leading tags, and max tag cap."""
    if not text:
        return ""

    # Remove any tags at the very beginning of the string
    cleaned = re.sub(r"^\s*<[^>]+>\s*", "", text)

    tag_count = 0

    def replace_tag(match: re.Match) -> str:
        nonlocal tag_count
        tag = f"<{match.group(1).strip().lower()}>"
        if tag in ALLOWED_TAGS and tag_count < max_tags:
            tag_count += 1
            return tag
        return ""

    result = TAG_REGEX.sub(replace_tag, cleaned)
    # Collapse excess spaces
    return re.sub(r"\s+", " ", result).strip()


class ResponseComposer:
    """Composes dynamic, fact-grounded acknowledgments and single focused clarifications."""

    @staticmethod
    def _get_field_meta(field: str, language: str = "en-IN") -> tuple[str, str]:
        """Return (display_name, reason_explanation) for missing fields."""
        is_hi = language.startswith("hi") or language == "hinglish"
        if field == "full_name":
            display = "Full Legal Name" if not is_hi else "पूरा कानूनी नाम (Full Legal Name)"
            reason = (
                "to identify you as the claimant on the statutory notice"
                if not is_hi
                else "कानूनी नोटिस पर आपका नाम दर्ज करने के लिए"
            )
        elif field == "order_id":
            display = "Order ID or Reference Number" if not is_hi else "Order ID या ट्रांजैक्शन UTR"
            reason = (
                "to track the specific transaction with the company"
                if not is_hi
                else "कंपनी के साथ आपके ट्रांजैक्शन की पहचान के लिए"
            )
        elif field == "amount":
            display = "Amount Paid in INR" if not is_hi else "भुगतान की गई राशि (Amount in INR)"
            reason = (
                "to calculate statutory interest and legal damages"
                if not is_hi
                else "ब्याज और मुआवजे की सटीक गणना के लिए"
            )
        elif field == "incident_date":
            display = "Transaction or Incident Date" if not is_hi else "लेनदेन या घटना की तारीख (Date)"
            reason = (
                "to establish the limitation period and interest timeline"
                if not is_hi
                else "समय सीमा और ब्याज की अवधि निर्धारित करने के लिए"
            )
        elif field == "brand":
            display = "Company or Brand Name" if not is_hi else "कंपनी या ब्रांड का नाम (Brand Name)"
            reason = (
                "to address the notice to the correct statutory entity"
                if not is_hi
                else "संबंधित कंपनी के नोडल अधिकारी को नोटिस भेजने के लिए"
            )
        else:
            display = field.replace("_", " ").title()
            reason = "to complete your legal grievance filing"
        return display, reason

    @classmethod
    def compose_clarification_template(
        cls,
        known_facts: dict[str, Any],
        target_field: str,
        language: str = "en-IN",
    ) -> ComposedResponse:
        """Deterministic, fact-grounded fallback template composer."""
        is_hi = language.startswith("hi") or language == "hinglish"
        display_name, reason = cls._get_field_meta(target_field, language)

        brand = known_facts.get("brand") or known_facts.get("brand_raw")
        amount = known_facts.get("amount") or known_facts.get("amount_paid_inr")
        name = known_facts.get("full_name") or known_facts.get("complainant_full_name")
        order_id = known_facts.get("order_id")

        ack_parts: list[str] = []
        spoken_ack_parts: list[str] = []

        if not is_hi:
            if brand and amount:
                amt_str = format_inr(float(amount))
                ack_parts.append(f"I have recorded your dispute regarding <b>{brand}</b> for <b>{amt_str}</b>.")
                spoken_ack_parts.append(f"I have recorded your dispute regarding {brand} for {amt_str}.")
            elif brand:
                ack_parts.append(f"I have noted your dispute regarding <b>{brand}</b>.")
                spoken_ack_parts.append(f"I have noted your dispute regarding {brand}.")
            elif amount:
                amt_str = format_inr(float(amount))
                ack_parts.append(f"I have recorded your payment of <b>{amt_str}</b>.")
                spoken_ack_parts.append(f"I have recorded your payment of {amt_str}.")

            if order_id and target_field != "order_id":
                ack_parts.append(f"Order reference <b>{order_id}</b> is saved.")
                spoken_ack_parts.append(f"Order reference {order_id} is saved.")

            if name and target_field != "full_name":
                ack_parts.append(f"Claimant name: <b>{name}</b>.")

            ack_text = " ".join(ack_parts)
            spoken_ack = " ".join(spoken_ack_parts)

            visible = (
                f"{ack_text + '<br><br>' if ack_text else ''}"
                f"<b>Required Detail:</b> Please provide your <b>{display_name}</b> {reason}."
            )
            spoken = (
                f"{spoken_ack} <pauses> " if spoken_ack else ""
            ) + f"Please provide your {display_name} {reason}."
        else:
            if brand and amount:
                amt_str = format_inr(float(amount))
                ack_parts.append(f"मैंने <b>{brand}</b> के खिलाफ <b>{amt_str}</b> की आपकी शिकायत दर्ज कर ली है।")
                spoken_ack_parts.append(f"Maine {brand} ke khilaaf {amt_str} ki aapki shikayat darj kar li hai.")
            elif brand:
                ack_parts.append(f"मैंने <b>{brand}</b> से संबंधित आपकी शिकायत नोट कर ली है।")
                spoken_ack_parts.append(f"Maine {brand} se sambandhit aapki shikayat note kar li hai.")

            if order_id and target_field != "order_id":
                ack_parts.append(f"ऑर्डर संदर्भ <b>{order_id}</b> सुरक्षित है।")
                spoken_ack_parts.append(f"Order sandarbh {order_id} surakshit hai.")

            ack_text = " ".join(ack_parts)
            spoken_ack = " ".join(spoken_ack_parts)

            visible = (
                f"{ack_text + '<br><br>' if ack_text else ''}"
                f"<b>आवश्यक जानकारी:</b> {reason}, कृपया अपना <b>{display_name}</b> बताएं।"
            )
            spoken = (
                f"{spoken_ack} <pauses> " if spoken_ack else ""
            ) + f"{reason}, kripya apna {display_name} batayein."

        spoken_clean = sanitize_speech_tags(spoken)
        return ComposedResponse(
            visible_text=visible,
            spoken_text=spoken_clean,
            target_field=target_field,
        )

    @classmethod
    async def compose_clarification(
        cls,
        known_facts: dict[str, Any],
        target_field: str,
        language: str = "en-IN",
        latest_user_text: str | None = None,
    ) -> ComposedResponse:
        """Compose dynamic clarification response via LLM with deterministic fallback."""
        display_name, reason = cls._get_field_meta(target_field, language)

        # Attempt dynamic LLM composition if Gemini key is present
        if settings.gemini_api_key:
            try:
                from google import genai
                from google.genai import types

                facts_summary = {
                    k: v
                    for k, v in known_facts.items()
                    if v is not None and k in {"brand", "brand_raw", "amount", "amount_paid_inr", "order_id", "incident_date", "complainant_full_name", "full_name"}
                }

                system_prompt = (
                    "You are SAARTHI (pronounced saar-thee), an honest, context-aware Indian consumer dispute assistant. "
                    "Your mission is to generate a dynamic, respectful, single-field clarification response grounded strictly in what the user stated. "
                    "STRICT RULES:\n"
                    "1. Do NOT use any emoji anywhere.\n"
                    "2. Acknowledge the user's specific context naturally without repetitive boilerplate.\n"
                    "3. Ground your statement in known facts only. Never invent order numbers, brand misconduct, or guaranteed outcomes.\n"
                    "4. Ask for EXACTLY ONE missing detail: the target field.\n"
                    "5. In 'spoken_text', start with plain natural speech without leading emotional tags (<sigh>, <excited>, <whispers>). "
                    "You may use at most one <pauses> tag if needed.\n"
                    "6. Return ONLY valid JSON with keys 'visible_text' (Telegram HTML format) and 'spoken_text'."
                )

                user_prompt = (
                    f"Known Facts: {json.dumps(facts_summary)}\n"
                    f"Latest User Statement: \"{latest_user_text or ''}\"\n"
                    f"Target Missing Field: {target_field} ({display_name})\n"
                    f"Why Needed: {reason}\n"
                    f"Language: {language}\n"
                )

                client = genai.Client(
                    api_key=settings.gemini_api_key,
                    http_options=types.HttpOptions(timeout=10000),
                )
                response = await client.aio.models.generate_content(
                    model=settings.llm_model,
                    contents=f"{system_prompt}\n\n{user_prompt}",
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = text.strip("`").replace("json\n", "")
                data = json.loads(text)
                visible = data.get("visible_text", "")
                spoken = data.get("spoken_text", "")

                if visible and spoken:
                    spoken_clean = sanitize_speech_tags(spoken)
                    return ComposedResponse(
                        visible_text=visible,
                        spoken_text=spoken_clean,
                        target_field=target_field,
                    )
            except Exception as e:
                logger.warning(f"Dynamic LLM clarification composition failed, using fallback: {e}")

        # Fallback to deterministic template
        return cls.compose_clarification_template(known_facts, target_field, language)
