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
from saarthi.agent.llm_router import get_candidate_models, MODEL_DISPLAY_NAMES

logger = logging.getLogger(__name__)

# Allowed speech tags for Timbre v3.0 per PRD
ALLOWED_TAGS = {"<pauses>", "<slow>"}
TAG_REGEX = re.compile(r"<([^>]+)>")


@dataclass
class ComposedResponse:
    visible_text: str
    spoken_text: str
    target_field: str
    engine: str = "Neurons Nano"


async def _notify_progress(cb: Any, text: str) -> None:
    if not cb:
        return
    try:
        import inspect
        if inspect.iscoroutinefunction(cb):
            await cb(text)
        elif callable(cb):
            res = cb(text)
            if inspect.isawaitable(res):
                await res
    except Exception:
        pass


def sanitize_speech_tags(text: str, max_tags: int = 1) -> str:
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

            if ack_text:
                visible = (
                    f"{ack_text}<br><br>"
                    f"To finalize your statutory claim notice, please provide your <b>{display_name}</b> ({reason})."
                )
                spoken = f"{spoken_ack} <pauses> Please provide your {display_name} {reason}."
            else:
                visible = (
                    f"To assist with your consumer dispute filing, please provide your <b>{display_name}</b> ({reason})."
                )
                spoken = f"Please provide your {display_name} {reason}."
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

            if ack_text:
                visible = (
                    f"{ack_text}<br><br>"
                    f"कानूनी नोटिस तैयार करने के लिए, {reason}, कृपया अपना <b>{display_name}</b> बताएं।"
                )
                spoken = f"{spoken_ack} <pauses> {reason}, kripya apna {display_name} batayein."
            else:
                visible = (
                    f"आपकी कानूनी शिकायत को आगे बढ़ाने के लिए, {reason}, कृपया अपना <b>{display_name}</b> बताएं।"
                )
                spoken = f"{reason}, kripya apna {display_name} batayein."

        spoken_clean = sanitize_speech_tags(spoken)
        return ComposedResponse(
            visible_text=visible,
            spoken_text=spoken_clean,
            target_field=target_field,
            engine="Standard Engine",
        )

    @classmethod
    async def compose_clarification(
        cls,
        known_facts: dict[str, Any],
        target_field: str,
        language: str = "en-IN",
        latest_user_text: str | None = None,
        voice_character: str = "Shivani",
        progress_callback: Any = None,
        preferred_model: str | None = None,
    ) -> ComposedResponse:
        """Compose dynamic clarification response via OpenRouter -> Gemini -> Template cascade."""
        display_name, reason = cls._get_field_meta(target_field, language)
        gender = "female" if voice_character.lower() in {"shivani", "chetana", "kalpana", "lakshmi", "riyaa", "tarika", "vasudha"} else "male"

        facts_summary = {
            k: v
            for k, v in known_facts.items()
            if v is not None and k in {
                "brand", "brand_raw", "amount", "amount_paid_inr",
                "order_id", "incident_date", "complainant_full_name",
                "full_name", "dispute_category", "issue_type"
            }
        }

        system_prompt = (
            "You are SAARTHI, an empathetic, respectful, and highly competent Indian consumer dispute assistant. "
            "You assist consumers in resolving disputes with companies under the Consumer Protection Act, 2019.\n\n"
            "SYSTEM KNOWLEDGE:\n"
            "SAARTHI supports 10 official Indian languages via Gnani Speech AI: Hindi (हिन्दी), English, Kannada (ಕನ್ನಡ), Tamil (தமிழ்), Telugu (తెలుగు), Marathi (मराठी), Bengali (বাংলা), Gujarati (ગુજરાતી), Malayalam (മലയാളം), and Punjabi (ਪੰਜਾਬੀ). Never say you only support Hindi and English.\n\n"
            "YOUR OBJECTIVE:\n"
            "Compose a natural, reassuring response that acknowledges what the user just said, "
            "summarizes key facts gently, and asks for EXACTLY ONE missing detail.\n\n"
            "STRICT GUIDELINES:\n"
            "1. NO EMOJIS: Do not include emojis anywhere in visible_text or spoken_text.\n"
            "2. ACKNOWLEDGE & VALIDATE: Warmly acknowledge the user's latest statement and confirmed facts (e.g., brand, amount, or order ID) naturally.\n"
            f"3. ASK ONLY ONE FIELD: Ask exclusively for the target missing detail, explicitly mentioning '{display_name}'. Explain briefly and naturally why it is needed.\n"
            f"4. VOICE GENDER CONCORDANCE: You are speaking as '{voice_character}' ({gender.upper()}). "
            f"When using Hindi or Hinglish, strictly conjugate first-person verbs for {gender.upper()} gender "
            f"(e.g., female uses 'karungi', 'bataungi', 'sun rahi hoon'; male uses 'karunga', 'bataunga', 'sun raha hoon').\n"
            "5. FULL SPOKEN TEXT FOR TTS: 'spoken_text' MUST speak the full response completely and naturally, matching the information in 'visible_text' without HTML tags or markdown formatting. Do NOT cut off the audio or speak only half. You may include at most one <pauses> tag.\n"
            "6. OUTPUT FORMAT: Respond ONLY with a valid JSON object with keys 'visible_text' (HTML formatted for Telegram) and 'spoken_text'."
        )

        user_prompt = (
            f"Known Facts: {json.dumps(facts_summary, ensure_ascii=False)}\n"
            f"Latest User Statement: \"{latest_user_text or ''}\"\n"
            f"Target Missing Field: {target_field} ({display_name})\n"
            f"Why Needed: {reason}\n"
            f"Language: {language}\n"
            f"Voice Character: {voice_character} ({gender})\n"
        )

        # Tier 1: Neurons Nano (OpenRouter Free Models)
        if settings.openrouter_api_key:
            candidate_models = get_candidate_models(preferred_model)
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://github.com/codebysnorlax/Saarthi",
                "X-Title": "SAARTHI Consumer Grievance Assistant",
            }
            for model_name in candidate_models:
                display = MODEL_DISPLAY_NAMES.get(model_name, model_name.split("/")[-1].replace(":free", ""))
                await _notify_progress(progress_callback, f"Connecting to Neurons Nano ({display})...")
                try:
                    async with httpx.AsyncClient(timeout=7.0) as http_client:
                        res = await http_client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers=headers,
                            json={
                                "model": model_name,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                                "temperature": 0.4,
                            },
                        )
                        if res.status_code == 200:
                            content = res.json()["choices"][0]["message"]["content"].strip()
                            if content.startswith("```"):
                                content = re.sub(r"^```(?:json)?\n", "", content)
                                content = re.sub(r"\n```$", "", content)
                            data = json.loads(content)
                            visible = data.get("visible_text")
                            spoken = data.get("spoken_text")
                            if visible and spoken:
                                await _notify_progress(progress_callback, f"Connected to Neurons Nano ({display})\nThinking...")
                                return ComposedResponse(
                                    visible_text=visible,
                                    spoken_text=sanitize_speech_tags(spoken, max_tags=1),
                                    target_field=target_field,
                                    engine=f"Neurons Nano ({display})",
                                )
                        else:
                            logger.warning(f"OpenRouter model {model_name} returned status {res.status_code}")
                except Exception as e:
                    logger.warning(f"OpenRouter attempt failed on {model_name}: {e}")

        # Tier 2: Neurons Mini (Google Gemini API / Groq)
        if settings.gemini_api_key:
            await _notify_progress(progress_callback, "Could not connect to Neurons Nano. Connecting to Neurons Mini...")
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(
                    api_key=settings.gemini_api_key,
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
                    if not gem_model or ":free" in gem_model or gem_model in seen_gemini:
                        continue
                    seen_gemini.add(gem_model)
                    try:
                        response = await client.aio.models.generate_content(
                            model=gem_model,
                            contents=f"{system_prompt}\n\n{user_prompt}",
                        )
                        text = response.text.strip()
                        if text.startswith("```"):
                            text = re.sub(r"^```(?:json)?\n", "", text)
                            text = re.sub(r"\n```$", "", text)
                        data = json.loads(text)
                        visible = data.get("visible_text")
                        spoken = data.get("spoken_text")
                        if visible and spoken:
                            await _notify_progress(progress_callback, "Connected to Neurons Mini\nThinking...")
                            return ComposedResponse(
                                visible_text=visible,
                                spoken_text=sanitize_speech_tags(spoken, max_tags=1),
                                target_field=target_field,
                                engine="Neurons Mini",
                            )
                    except Exception as ge:
                        logger.warning(f"Dynamic Gemini clarification composition failed on {gem_model}: {ge}")
            except Exception as e:
                logger.warning(f"Dynamic Gemini clarification composition failed: {e}")

        if settings.groq_api_key:
            try:
                from groq import AsyncGroq
                client = AsyncGroq(api_key=settings.groq_api_key)
                completion = await client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    timeout=5.0,
                )
                content = completion.choices[0].message.content
                data = json.loads(content)
                visible = data.get("visible_text")
                spoken = data.get("spoken_text")
                if visible and spoken:
                    await _notify_progress(progress_callback, "Connected to Neurons Mini\nThinking...")
                    return ComposedResponse(
                        visible_text=visible,
                        spoken_text=sanitize_speech_tags(spoken, max_tags=1),
                        target_field=target_field,
                        engine="Neurons Mini",
                    )
            except Exception as e:
                logger.warning(f"Dynamic Groq clarification composition failed: {e}")

        # Tier 3: Deterministic Fallback Template (Standard Engine)
        await _notify_progress(progress_callback, "Could not connect to Neurons. Using standard engine...")
        return cls.compose_clarification_template(known_facts, target_field, language)

    @classmethod
    async def compose_conversation(
        cls,
        user_text: str,
        language: str = "en-IN",
        voice_character: str = "Shivani",
        progress_callback: Any = None,
        preferred_model: str | None = None,
    ) -> ComposedResponse:
        """Dynamically compose conversational responses (languages, capabilities, rights, greetings) via LLM Router Brain."""
        gender = "female" if voice_character.lower() in {"shivani", "chetana", "kalpana", "lakshmi", "riyaa", "tarika", "vasudha"} else "male"

        system_prompt = (
            "You are SAARTHI, an intelligent, empathetic, and respectful Voice-First Indian Consumer Rights and Dispute Guide under the Consumer Protection Act, 2019.\n\n"
            "CRITICAL KNOWLEDGE BASE:\n"
            "1. SUPPORTED LANGUAGES: SAARTHI proudly supports 10 official Indian languages via Gnani Speech AI:\n"
            "   - Hindi (हिन्दी)\n"
            "   - English\n"
            "   - Kannada (ಕನ್ನಡ)\n"
            "   - Tamil (தமிழ்)\n"
            "   - Telugu (తెలుగు)\n"
            "   - Marathi (मराठी)\n"
            "   - Bengali (বাংলা)\n"
            "   - Gujarati (ગુજરાતી)\n"
            "   - Malayalam (മലയാളം)\n"
            "   - Punjabi (ਪੰਜਾਬੀ)\n"
            "   Plus conversational Hinglish. When asked about languages, explicitly and proudly mention that SAARTHI supports all these 10 Indian languages, and users can switch anytime using /lang or the menu.\n"
            "2. VOICE PERSONAS: Powered by Gnani Timbre v3.0 with verified voices: Shivani (Female, Empathetic), Devansh (Male, Conversational), Chetana (Female, Customer Care). Switch via /gender.\n"
            "3. NEURONS AI BRAIN: OpenRouter free models including Nemotron 3.5 Super VL, North Mini Code, Nemotron 3 Nano Omni 30B, and Auto. Switch via /neurons.\n"
            "4. CONSUMER DISPUTE ASSISTANCE: SAARTHI assists consumers against unfair practices by e-commerce platforms, airlines, banks, and brands (refund delays, defective products, cancelled tickets, hidden fees, failed UPI debits) by drafting:\n"
            "   - Formal Legal Demand Notice (PDF) for brand Nodal Grievance Officer.\n"
            "   - National Consumer Helpline (NCH 1915) WhatsApp dossier.\n"
            "   - Public Social Escalation post for X (Twitter).\n"
            "   - Voice walkthrough in user's chosen language and voice persona.\n\n"
            "STRICT GUIDELINES:\n"
            "1. NO EMOJIS: Do NOT include any emojis anywhere in visible_text or spoken_text.\n"
            f"2. GENDER CONCORDANCE: You are speaking as '{voice_character}' ({gender.upper()}). "
            f"When answering in Hindi or Hinglish, strictly conjugate first-person verbs for {gender.upper()} gender (e.g., female uses 'karungi', 'bata sakti hoon', 'madad karungi'; male uses 'karunga', 'bata sakta hoon', 'madad karunga').\n"
            "3. FULL SPOKEN TEXT FOR TTS: 'spoken_text' MUST speak the full response completely and naturally, matching the information in 'visible_text' without HTML tags or markdown formatting. Do NOT cut off the audio or speak only half. You may include at most one <pauses> tag.\n"
            "4. DYNAMIC & NATURAL: Respond conversationally, accurately, and directly to what the user said. When user asks about capabilities, what you can do, or introduces themselves, explain how you help consumers under the Consumer Protection Act, 2019 by calculating statutory claims and drafting a formal Legal Demand Notice (PDF), NCH 1915 dossier, and social escalation posts. Never output canned boilerplate. Warmly invite them to share their dispute whenever they are ready.\n"
            "5. OUTPUT FORMAT: Respond ONLY with a valid JSON object with keys 'visible_text' (HTML formatted for Telegram using <b>, <i>, <code>) and 'spoken_text' (plain conversational text for TTS)."
        )

        user_prompt = (
            f"User Query: \"{user_text}\"\n"
            f"Language: {language}\n"
            f"Voice Character: {voice_character} ({gender})\n"
        )

        # Tier 1: Neurons Nano (OpenRouter Free Models)
        if settings.openrouter_api_key:
            candidate_models = get_candidate_models(preferred_model)
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": "https://github.com/codebysnorlax/Saarthi",
                "X-Title": "SAARTHI Consumer Grievance Assistant",
            }
            for model_name in candidate_models:
                display = MODEL_DISPLAY_NAMES.get(model_name, model_name.split("/")[-1].replace(":free", ""))
                await _notify_progress(progress_callback, f"Connecting to Neurons Nano ({display})...")
                try:
                    async with httpx.AsyncClient(timeout=7.0) as http_client:
                        res = await http_client.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers=headers,
                            json={
                                "model": model_name,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ],
                                "temperature": 0.4,
                            },
                        )
                        if res.status_code == 200:
                            content = res.json()["choices"][0]["message"]["content"].strip()
                            if content.startswith("```"):
                                content = re.sub(r"^```(?:json)?\n", "", content)
                                content = re.sub(r"\n```$", "", content)
                            data = json.loads(content)
                            visible = data.get("visible_text")
                            spoken = data.get("spoken_text")
                            if visible and spoken:
                                await _notify_progress(progress_callback, f"Connected to Neurons Nano ({display})\nThinking...")
                                return ComposedResponse(
                                    visible_text=visible,
                                    spoken_text=sanitize_speech_tags(spoken, max_tags=1),
                                    target_field="general_conversation",
                                    engine=f"Neurons Nano ({display})",
                                )
                except Exception as e:
                    logger.warning(f"OpenRouter conversation attempt failed on {model_name}: {e}")

        # Tier 2: Neurons Mini (Gemini / Groq)
        if settings.gemini_api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(
                    api_key=settings.gemini_api_key,
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
                    if not gem_model or ":free" in gem_model or gem_model in seen_gemini:
                        continue
                    seen_gemini.add(gem_model)
                    try:
                        response = await client.aio.models.generate_content(
                            model=gem_model,
                            contents=f"{system_prompt}\n\n{user_prompt}",
                        )
                        text = response.text.strip()
                        if text.startswith("```"):
                            text = re.sub(r"^```(?:json)?\n", "", text)
                            text = re.sub(r"\n```$", "", text)
                        data = json.loads(text)
                        visible = data.get("visible_text")
                        spoken = data.get("spoken_text")
                        if visible and spoken:
                            return ComposedResponse(
                                visible_text=visible,
                                spoken_text=sanitize_speech_tags(spoken, max_tags=1),
                                target_field="general_conversation",
                                engine="Neurons Mini",
                            )
                    except Exception as ge:
                        logger.warning(f"Gemini conversation failed on {gem_model}: {ge}")
            except Exception as e:
                logger.warning(f"Gemini conversation attempt failed: {e}")

        # Fallback Dynamic Template
        is_hi = language.startswith("hi") or "hinglish" in language.lower()
        if is_hi:
            verb_help = "मदद करूँगी" if gender == "female" else "मदद करूंगा"
            verb_help_spoken = "karungi" if gender == "female" else "karunga"
            visible = (
                f"<b>नमस्ते! मैं सारथी (SAARTHI) से {voice_character} हूँ।</b>\n\n"
                f"मैं <b>उपभोक्ता संरक्षण कानून (Consumer Protection Act, 2019)</b> के तहत नोडल अधिकारी के लिए <b>लीगल डिमांड नोटिस (Legal Demand Notice PDF)</b> और राष्ट्रीय उपभोक्ता हेल्पलाइन (NCH 1915) ड्राफ्ट तैयार करके आपकी {verb_help}।\n\n"
                f"सारथी Gnani Speech AI द्वारा संचालित <b>10 भारतीय भाषाओं</b> का समर्थन करता है:\n"
                f"• हिन्दी (Hindi), English, ಕನ್ನಡ (Kannada), தமிழ் (Tamil)\n"
                f"• Telugu (తెలుగు), मराठी (Marathi), বাংলা (Bengali), ગુજરાતી (Gujarati)\n"
                f"• Malayalam (മലയാളം), ਪੰਜਾਬੀ (Punjabi)\n\n"
                f"आप मेनू से कभी भी अपनी भाषा (/lang), आवाज़ (/gender), या AI मॉडल (/neurons) बदल सकते हैं।\n\n"
                f"अगर किसी कंपनी या विक्रेता के साथ आपकी कोई समस्या या रिफंड अटका है, तो मुझे बताएं, मैं आपकी पूरी {verb_help}!"
            )
            spoken = (
                f"Namaste! Main SAARTHI se {voice_character} hoon. <pauses> "
                f"Consumer Protection Act ke tehat main legal demand notice aur consumer helpline dossier taiyaar karke madad {verb_help_spoken}. "
                f"SAARTHI 10 Bharatiya bhashaon ka samarthan karta hai, jaise Hindi, English, Tamil, Telugu, Kannada, Marathi, Bengali, Gujarati, Malayalam, aur Punjabi. "
                f"Agar kisi company ke saath aapka koi dispute ya refund atka hai, toh kripya batayein, main aapki poori madad {verb_help_spoken}."
            )
        else:
            visible = (
                f"<b>Hello! I am {voice_character} from SAARTHI.</b>\n\n"
                f"I help consumers resolve unfair disputes under the <b>Consumer Protection Act, 2019</b> by calculating statutory claims and drafting a formal <b>Legal Demand Notice (PDF)</b>, NCH 1915 WhatsApp filings, and social escalation posts.\n\n"
                f"SAARTHI proudly supports <b>10 Indian languages</b> via Gnani Speech AI:\n"
                f"• Hindi (हिन्दी), English, Kannada (ಕನ್ನಡ), Tamil (தமிழ்)\n"
                f"• Telugu (తెలుగు), Marathi (मराठी), Bengali (বাংলা), Gujarati (ગુજરાતી)\n"
                f"• Malayalam (മലയാളം), Punjabi (ਪੰਜਾਬੀ)\n\n"
                f"You can switch your language anytime using /lang or the menu buttons below, change voice character via /gender, and select AI Neurons via /neurons.\n\n"
                f"Please tell me which company or brand you have an issue with, and what happened!"
            )
            spoken = (
                f"Hello! I am {voice_character} from SAARTHI. <pauses> "
                f"I assist consumers under the Consumer Protection Act by generating formal legal demand notices and consumer helpline filings. "
                f"SAARTHI supports 10 Indian languages via Gnani Speech AI, including Hindi, English, Kannada, Tamil, Telugu, Marathi, Bengali, Gujarati, Malayalam, and Punjabi. "
                f"Please tell me which company you have an issue with and what happened, and I will assist you."
            )

        return ComposedResponse(
            visible_text=visible,
            spoken_text=sanitize_speech_tags(spoken, max_tags=1),
            target_field="general_conversation",
            engine="Standard Engine",
        )
