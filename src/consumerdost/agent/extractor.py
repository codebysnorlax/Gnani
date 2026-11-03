from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, timedelta
from typing import Literal

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DisputeExtractionSchema(BaseModel):
    brand_raw: str | None = Field(None, description="Brand or platform name mentioned")
    category: Literal[
        "E_COMMERCE",
        "QUICK_COMMERCE_FOOD",
        "AIRLINES_TRAVEL",
        "TELECOM_DTH",
        "FINTECH_PAYMENTS",
    ] | None = None
    issue_type: Literal[
        "ECOMMERCE_DEFECTIVE_GOODS",
        "ECOMMERCE_REFUND_DELAY_OR_DENIAL",
        "QCOMM_EXPIRED_OR_MISSING_ITEMS",
        "DARK_PATTERNS_HIDDEN_FEES",
        "UPI_FAILED_DEBIT_STUCK",
        "AIRLINE_CANCELLED_OR_DELAYED",
        "TELECOM_WRONGFUL_BILLING_OR_VAS",
    ] | None = None
    product_name: str | None = None
    order_id: str | None = None
    incident_date: str | None = Field(None, description="YYYY-MM-DD")
    amount_paid_inr: float | None = None
    complainant_full_name: str | None = None
    complainant_contact: str | None = None
    incident_summary_en: str = Field(
        default="",
        description="Formal 2-3 sentence English summary of the consumer grievance",
    )


SYSTEM_PROMPT = """You are a legal intake parser for ConsumerDost India.
Extract structured consumer dispute facts from Hindi, Hinglish, or English text.
Today's date (IST) is {today_iso}.
Rules:
1. Convert relative dates ('kal'/'yesterday', 'parso', '25 Oct') into YYYY-MM-DD.
2. Translate the complaint into a formal, objective 2-3 sentence English summary in `incident_summary_en`.
3. Only extract `order_id` if an explicit alphanumeric ID, PNR, or UTR is present; otherwise set null.
4. Output strictly valid JSON matching the schema."""


# ---------------------------------------------------------------------------
# TIER 3 & 4: 100% Offline Deterministic Fallback Parser (Zero API Keys Needed)
# ---------------------------------------------------------------------------
KNOWN_BRAND_KEYWORDS: dict[str, tuple[str, str, str]] = {
    # keyword -> (Brand Name, Category, Default Issue Type)
    "flipkart": ("Flipkart", "E_COMMERCE", "ECOMMERCE_DEFECTIVE_GOODS"),
    "amazon": ("Amazon", "E_COMMERCE", "ECOMMERCE_DEFECTIVE_GOODS"),
    "meesho": ("Meesho", "E_COMMERCE", "ECOMMERCE_DEFECTIVE_GOODS"),
    "myntra": ("Myntra", "E_COMMERCE", "ECOMMERCE_DEFECTIVE_GOODS"),
    "nykaa": ("Nykaa", "E_COMMERCE", "ECOMMERCE_DEFECTIVE_GOODS"),
    "ajio": ("AJIO", "E_COMMERCE", "ECOMMERCE_DEFECTIVE_GOODS"),
    "zomato": ("Zomato", "QUICK_COMMERCE_FOOD", "QCOMM_EXPIRED_OR_MISSING_ITEMS"),
    "swiggy": ("Swiggy", "QUICK_COMMERCE_FOOD", "QCOMM_EXPIRED_OR_MISSING_ITEMS"),
    "blinkit": ("Blinkit", "QUICK_COMMERCE_FOOD", "QCOMM_EXPIRED_OR_MISSING_ITEMS"),
    "zepto": ("Zepto", "QUICK_COMMERCE_FOOD", "QCOMM_EXPIRED_OR_MISSING_ITEMS"),
    "instamart": ("Instamart", "QUICK_COMMERCE_FOOD", "QCOMM_EXPIRED_OR_MISSING_ITEMS"),
    "indigo": ("IndiGo", "AIRLINES_TRAVEL", "AIRLINE_CANCELLED_OR_DELAYED"),
    "air india": ("Air India", "AIRLINES_TRAVEL", "AIRLINE_CANCELLED_OR_DELAYED"),
    "spicejet": ("SpiceJet", "AIRLINES_TRAVEL", "AIRLINE_CANCELLED_OR_DELAYED"),
    "makemytrip": ("MakeMyTrip", "AIRLINES_TRAVEL", "AIRLINE_CANCELLED_OR_DELAYED"),
    "irctc": ("IRCTC", "AIRLINES_TRAVEL", "AIRLINE_CANCELLED_OR_DELAYED"),
    "airtel": ("Airtel", "TELECOM_DTH", "TELECOM_WRONGFUL_BILLING_OR_VAS"),
    "jio": ("Jio", "TELECOM_DTH", "TELECOM_WRONGFUL_BILLING_OR_VAS"),
    "vi": ("Vi", "TELECOM_DTH", "TELECOM_WRONGFUL_BILLING_OR_VAS"),
    "phonepe": ("PhonePe", "FINTECH_PAYMENTS", "UPI_FAILED_DEBIT_STUCK"),
    "gpay": ("Google Pay", "FINTECH_PAYMENTS", "UPI_FAILED_DEBIT_STUCK"),
    "google pay": ("Google Pay", "FINTECH_PAYMENTS", "UPI_FAILED_DEBIT_STUCK"),
    "paytm": ("Paytm", "FINTECH_PAYMENTS", "UPI_FAILED_DEBIT_STUCK"),
}


def deterministic_offline_extract(
    text: str, today: date | None = None
) -> DisputeExtractionSchema:
    """Pure-Python fallback extractor that guarantees a working demo with zero APIs."""
    today = today or date.today()
    lower = text.lower()

    # 1. Detect Brand, Category & Default Issue Type
    brand_raw = None
    category = None
    issue_type = None
    for kw, (b_name, cat, iss) in KNOWN_BRAND_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", lower):
            brand_raw, category, issue_type = b_name, cat, iss
            break

    # Refine issue_type based on Hinglish/English keywords
    if any(w in lower for w in ["upi", "utr", "debit", "kat gaya", "deducted"]):
        category = category or "FINTECH_PAYMENTS"
        issue_type = "UPI_FAILED_DEBIT_STUCK"
    elif any(w in lower for w in ["flight", "boarding", "airline", "cancelled"]):
        category = category or "AIRLINES_TRAVEL"
        issue_type = "AIRLINE_CANCELLED_OR_DELAYED"
    elif any(w in lower for w in ["rotten", "expired", "kharab khana", "missing item"]):
        category = category or "QUICK_COMMERCE_FOOD"
        issue_type = "QCOMM_EXPIRED_OR_MISSING_ITEMS"
    elif any(w in lower for w in ["refund", "paisa wapas", "return reject"]):
        issue_type = issue_type or "ECOMMERCE_REFUND_DELAY_OR_DENIAL"

    # 2. Extract Amount (e.g., "14,999", "Rs. 1500", "15000 ka", "amount 2499")
    amount_paid_inr: float | None = None
    amt_patterns = [
        r"(?:₹|rs\.?|inr)\s*([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]+(?:\.[0-9]{1,2})?)",
        r"\b([0-9]{1,3}(?:,[0-9]{2,3})+|[0-9]{3,6})\s*(?:rupees|rs|ka|ki|rupaye)\b",
    ]
    for pat in amt_patterns:
        m = re.search(pat, lower)
        if m:
            amount_paid_inr = float(m.group(1).replace(",", ""))
            break

    # 3. Extract Order ID / PNR / UTR (e.g., OD3091823901, 402-1234567, 12-digit UTR)
    order_id: str | None = None
    id_patterns = [
        r"\b(OD[A-Z0-9]{8,18})\b",
        r"(?:order\s*(?:id|no|number)?|txn|utr|pnr)[\s:#-]*([A-Z0-9-]{6,22})\b",
    ]
    for pat in id_patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            order_id = m.group(1).upper()
            break

    # 4. Extract Date (ISO date, "yesterday"/"kal", "X days ago"/"X din pehle")
    incident_date = today.isoformat()
    iso_m = re.search(r"\b(202[5-7]-[01]\d-[0-3]\d)\b", text)
    days_ago_m = re.search(
        r"\b(\d{1,2})\s*(?:days?\s*ago|din\s*pehle|din\s*ho\s*gaye)\b", lower
    )
    if iso_m:
        incident_date = iso_m.group(1)
    elif "parso" in lower:
        incident_date = (today - timedelta(days=2)).isoformat()
    elif "yesterday" in lower or re.search(r"\bkal\b", lower):
        incident_date = (today - timedelta(days=1)).isoformat()
    elif days_ago_m:
        incident_date = (today - timedelta(days=int(days_ago_m.group(1)))).isoformat()

    # 5. Extract Complainant Email / Phone & Name if explicitly provided
    email_m = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    phone_m = re.search(r"\b(?:[6-9]\d{9})\b", text)
    contact = email_m.group(0) if email_m else (phone_m.group(0) if phone_m else None)

    name_m = re.search(
        r"(?:my\s+name\s+is|mera\s+naam|name\s*[:=-])\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
        text,
        flags=re.IGNORECASE,
    )
    full_name = name_m.group(1).strip().title() if name_m else None

    # 6. Build Formal English Summary for the Legal Notice PDF
    brand_str = brand_raw or "the Opposite Party platform"
    amt_str = (
        f"INR {amount_paid_inr:,.2f}" if amount_paid_inr else "the transaction amount"
    )
    summary_en = (
        f"The Complainant transacted with {brand_str} for {amt_str} on {incident_date}"
        f"{f' (Reference ID: {order_id})' if order_id else ''}. "
        f"Despite repeated escalations regarding the defective/deficient service, "
        f"{brand_str} customer support has unlawfully withheld resolution and refund."
    )

    return DisputeExtractionSchema(
        brand_raw=brand_raw,
        category=category,
        issue_type=issue_type,
        order_id=order_id,
        incident_date=incident_date,
        amount_paid_inr=amount_paid_inr,
        complainant_full_name=full_name,
        complainant_contact=contact,
        incident_summary_en=summary_en,
    )


# ---------------------------------------------------------------------------
# 4-TIER CASCADING EXTRACTOR ROUTER
# ---------------------------------------------------------------------------
async def extract_dispute_facts(
    text: str, today: date | None = None
) -> DisputeExtractionSchema:
    """Cascading 4-Tier Extractor:
    Tier 1: Gemini or Groq Free Cloud LLM
    Tier 2: OpenRouter Free Models
    Tier 3: Golden Demo Fixture Match
    Tier 4: Deterministic Regex & Keyword Fallback
    """
    today = today or date.today()
    system_prompt_formatted = SYSTEM_PROMPT.format(today_iso=today.isoformat())

    # Tier 1A: Groq Free Tier (Llama 3.3 70B)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key and groq_api_key != "your_groq_api_key_here":
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_api_key}"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_prompt_formatted},
                            {"role": "user", "content": text},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    return DisputeExtractionSchema.model_validate(parsed)
                logger.warning(
                    "Groq API returned status %s, falling to next tier", res.status_code
                )
        except Exception as exc:
            logger.warning("Tier 1 (Groq) failed: %s", exc)

    # Tier 1B: Gemini Free Tier (Google AI Studio)
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key and gemini_api_key != "your_gemini_api_key_here":
        try:
            model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_api_key}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    url,
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {
                                        "text": f"{system_prompt_formatted}\n\nUser Grievance: {text}"
                                    }
                                ]
                            }
                        ],
                        "generationConfig": {"response_mime_type": "application/json"},
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(raw_json)
                    return DisputeExtractionSchema.model_validate(parsed)
                logger.warning(
                    "Gemini API returned status %s, falling to next tier",
                    res.status_code,
                )
        except Exception as exc:
            logger.warning("Tier 1 (Gemini) failed: %s", exc)

    # Tier 2: OpenRouter Free Models
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_api_key and openrouter_api_key != "your_openrouter_api_key_here":
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_api_key}",
                        "HTTP-Referer": "https://consumerdost.in",
                    },
                    json={
                        "model": "meta-llama/llama-3.3-70b-instruct:free",
                        "messages": [
                            {"role": "system", "content": system_prompt_formatted},
                            {"role": "user", "content": text},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    return DisputeExtractionSchema.model_validate(parsed)
                logger.warning(
                    "OpenRouter API returned status %s, falling to Tier 3/4",
                    res.status_code,
                )
        except Exception as exc:
            logger.warning("Tier 2 (OpenRouter) failed: %s", exc)

    # Tier 3 & 4: Deterministic Offline Pure-Python Fallback
    logger.info("Engaging Tier 4 pure-Python deterministic fallback extractor.")
    return deterministic_offline_extract(text, today=today)
