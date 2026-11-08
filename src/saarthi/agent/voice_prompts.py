"""Context-aware, natural voice prompt composer with Timbre v3.0 inline audio tags for all 10 Indic languages.

Strictly adheres to:
- SAARTHI identity (pronunciation included where helpful)
- No leading emotional tags (<excited>, <sigh>, <whispers>)
- Sparse validated tags (<pauses>, <slow>) with max 2 tags limit
- Dynamic grounding without presuming company misconduct or distress.
"""

from __future__ import annotations

import logging
from typing import Any
from saarthi.speech.gnani_tts import normalize_language_code
from saarthi.speech.tags import sanitize_tags_for_tts

logger = logging.getLogger(__name__)

# 1. Onboarding / Welcome Spoken Prompts
WELCOME_VOICE_TEMPLATES: dict[str, str] = {
    "hi-IN": (
        "Namaste! Main hoon SAARTHI. <pauses> "
        "Aapka consumer dispute sunkar turant legal notice aur helpline filing taiyaar karunga. "
        "<slow> Kripya ek voice note bhej kar batayein kya hua tha."
    ),
    "en-IN": (
        "Hello! I am SAARTHI, pronounced saar-thee. <pauses> "
        "I will convert your consumer grievance into a formal legal notice and helpline dossier. "
        "<slow> Please send a voice note describing what happened."
    ),
    "kn-IN": (
        "ನಮಸ್ಕಾರ! ನಾನು ಸಾರಥಿ (SAARTHI). <pauses> "
        "ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ಆಲಿಸಿ ಲೀಗಲ್ ನೋಟಿಸ್ ಮತ್ತು ಹೆಲ್ಪ್‌ಲೈನ್ ದೂರು ಸಿದ್ಧಪಡಿಸುತ್ತೇನೆ. "
        "<slow> ದಯವಿಟ್ಟು ಧ್ವನಿ ಸಂದೇಶ ಕಳುಹಿಸಿ."
    ),
    "ta-IN": (
        "வணக்கம்! நான் சாரதி (SAARTHI). <pauses> "
        "உங்கள் நுகர்வோர் புகாரைக் கேட்டு சட்ட அறிவிப்பு மற்றும் உதவி மையக் கோப்பை உருவாக்குவேன். "
        "<slow> உங்கள் குரல் பதிவை அனுப்புங்கள்."
    ),
    "te-IN": (
        "నమస్కారం! నేను సారథి (SAARTHI). <pauses> "
        "మీ సమస్యను విని లీగల్ నోటీసు మరియు హెల్ప్‌లైన్ ఫిర్యాదును సిద్ధం చేస్తాను. "
        "<slow> దయచేసి మీ వాయిస్ నోట్ పంపండి."
    ),
    "mr-IN": (
        "नमस्कार! मी सारथी (SAARTHI) आहे. <pauses> "
        "तुमची तक्रार ऐकून त्वरित कायदेशीर नोटीस आणि तक्रार अर्ज तयार करेन. "
        "<slow> कृपया व्हॉइस नोट पाठवा."
    ),
    "bn-IN": (
        "নমস্কার! আমি সারথী (SAARTHI)। <pauses> "
        "আপনার অভিযোগ শুনে আইনি নোটিশ এবং হেল্পলাইন ফাইল প্রস্তুত করব। "
        "<slow> দয়া করে একটি ভয়েস বার্তা পাঠান।"
    ),
    "gu-IN": (
        "નમસ્તે! હું સારથી (SAARTHI) છું. <pauses> "
        "તમારી ગ્રાહક ફરિયાદ સાંભળીને કાનૂની નોટિસ તૈયાર કરીશ. "
        "<slow> કૃપા કરીને તમારો વૉઇસ સંદેશ મોકલો."
    ),
    "ml-IN": (
        "നമസ്കാരം! ഞാൻ സാരഥി (SAARTHI). <pauses> "
        "നിങ്ങളുടെ പരാതി കേട്ട് നിയമപരമായ നോട്ടീസ് തയ്യാറാക്കാം. "
        "<slow> ദയവായി ഒരു വോയ്‌സ് നോട്ട് അയക്കൂ."
    ),
    "pa-IN": (
        "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਹਾਂ ਸਾਰਥੀ (SAARTHI)। <pauses> "
        "ਤੁਹਾਡੀ ਸ਼ਿਕਾਇਤ ਸੁਣ ਕੇ ਕਾਨੂੰਨੀ ਨੋਟਿਸ ਤਿਆਰ ਕਰਾਂਗਾ। "
        "<slow> ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਵੌਇਸ ਨੋਟ ਭੇਜੋ।"
    ),
}

# 2. General Clarification Voice Prompts
CLARIFICATION_VOICE_TEMPLATES: dict[str, str] = {
    "hi-IN": (
        "Legal notice complete karne ke liye kuch jankari chahiye. <pauses> "
        "<slow> Kripya apna Order ID, Transaction UTR, ya apna poora naam batayein."
    ),
    "en-IN": (
        "To finalize your statutory demand notice, a few details are required. <pauses> "
        "<slow> Please provide your Order ID, Transaction UTR, or your full legal name."
    ),
    "kn-IN": (
        "ಕಾನೂನು ನೋಟಿಸ್ ಪೂರ್ಣಗೊಳಿಸಲು ಕೆಲವು ವಿವರಗಳು ಬೇಕಾಗಿವೆ. <pauses> "
        "<slow> ದಯವಿಟ್ಟು ನಿಮ್ಮ ಆರ್ಡರ್ ಐಡಿ ಅಥವಾ ಪೂರ್ಣ ಹೆಸರನ್ನು ತಿಳಿಸಿ."
    ),
    "ta-IN": (
        "சட்ட அறிவிப்பை முடிக்க சில விவரங்கள் தேவை. <pauses> "
        "<slow> உங்கள் ஆர்டர் ஐடி அல்லது முழுப் பெயரைத் தெரிவிக்கவும்."
    ),
    "te-IN": (
        "చట్టపరమైన నోటీసు పూర్తి చేయడానికి కొన్ని వివరాలు అవసరం. <pauses> "
        "<slow> దయచేసి మీ ఆర్డర్ ఐడీ లేదా పూర్తి పేరును తెలియజేయండి."
    ),
    "mr-IN": (
        "कायदेशीर नोटीससाठी थोडी अधिक माहिती हवी आहे. <pauses> "
        "<slow> कृपया तुमचा ऑर्डर आयडी किंवा पूर्ण नाव सांगा."
    ),
    "bn-IN": (
        "আইনি নোটিশ তৈরি করতে কিছু অতিরিক্ত তথ্য প্রয়োজন। <pauses> "
        "<slow> অনুগ্রহ করে আপনার অর্ডার আইডি বা নাম বলুন।"
    ),
    "gu-IN": (
        "કાનૂની નોટિસ માટે કેટલીક વિગતોની જરૂર છે. <pauses> "
        "<slow> કૃપા કરીને તમારો ઓર્ડર આઈડી અથવા પૂરું નામ જણાવો."
    ),
    "ml-IN": (
        "നിയമപരമായ നോട്ടീസിനായി കൂടുതൽ വിവരങ്ങൾ ആവശ്യമുണ്ട്. <pauses> "
        "<slow> ദയവായി ഓർഡർ ഐഡിയോ പേരോ നൽകുക."
    ),
    "pa-IN": (
        "ਕਾਨੂੰਨੀ ਨੋਟਿਸ ਲਈ ਕੁਝ ਹੋਰ ਜਾਣਕਾਰੀ ਚਾਹੀਦੀ ਹੈ। <pauses> "
        "<slow> ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਆਰਡਰ ਆਈਡੀ ਜਾਂ ਪੂਰਾ ਨਾਮ ਦੱਸੋ।"
    ),
}

# 3. Assessment Walkthrough Voice Prompts
ASSESSMENT_VOICE_TEMPLATES: dict[str, str] = {
    "hi-IN": (
        "Aapka kanooni claim vishleshan taiyaar hai. <pauses> "
        "Consumer Protection Act ke tehat kul daawa rupaye {amount} banta hai. <pauses> "
        "Aage badhne ke liye screen par Review and generate documents chunein."
    ),
    "en-IN": (
        "Your legal dispute analysis is ready. <pauses> "
        "Under the Consumer Protection Act 2019, your total quantified claim is Rupees {amount}. <pauses> "
        "Please tap Review and generate documents on your screen to proceed."
    ),
    "kn-IN": (
        "ನಿಮ್ಮ ಕಾನೂನು ವಿಶ್ಲೇಷಣೆ ಸಿದ್ಧವಾಗಿದೆ. <pauses> "
        "ಗ್ರಾಹಕ ಸಂರಕ್ಷಣಾ ಕಾಯ್ದೆಯಡಿ ಒಟ್ಟು ಹಕ್ಕು ಮೊತ್ತ ರೂಪಾಯಿ {amount}. <pauses> "
        "ದಯವಿಟ್ಟು ಮುಂದುವರಿಯಲು Review and generate documents ಆಯ್ಕೆಮಾಡಿ."
    ),
    "ta-IN": (
        "உங்கள் சட்ட ஆய்வு தயாராக உள்ளது. <pauses> "
        "நுகர்வோர் பாதுகாப்புச் சட்டத்தின் கீழ் மொத்தக் கோரிக்கை ரூபாய் {amount}. <pauses> "
        "தொடர திரையில் Review and generate documents என்பதைத் தட்டவும்."
    ),
    "te-IN": (
        "మీ చట్టపరమైన విశ్లేషణ సిద్ధంగా ఉంది. <pauses> "
        "వినియోగదారుల రక్షణ చట్టం ప్రకారం మొత్తం క్లెయిమ్ రూపాయలు {amount}. <pauses> "
        "దయచేసి స్క్రీన్‌పై Review and generate documents ఎంచుకోండి."
    ),
    "mr-IN": (
        "तुमचे कायदेशीर विश्लेषण तयार आहे. <pauses> "
        "ग्राहक संरक्षण कायद्यानुसार एकूण मागणी रुपये {amount} आहे. <pauses> "
        "कृपया पुढे जाण्यासाठी स्क्रीनवर Review and generate documents निवडा."
    ),
    "bn-IN": (
        "আপনার আইনি বিশ্লেষণ প্রস্তুত। <pauses> "
        "ভোক্তা সুরক্ষা আইনের অধীনে মোট দাবি টাকা {amount}। <pauses> "
        "অনুগ্রহ করে এগিয়ে যেতে স্ক্রিনে Review and generate documents নির্বাচন করুন।"
    ),
    "gu-IN": (
        "તમારું કાનૂની વિશ્લેષણ તૈયાર છે. <pauses> "
        "ગ્રાહક સુરક્ષા કાયદા હેઠળ કુલ દાવો રૂપિયા {amount} થાય છે. <pauses> "
        "કૃપા કરીને આગળ વધવા સ્ક્રીન પર Review and generate documents પસંદ કરો."
    ),
    "ml-IN": (
        "നിങ്ങളുടെ നിയമപരമായ വിശകലനം തയ്യാറാണ്. <pauses> "
        "ഉപഭോക്തൃ സംരക്ഷണ നിയമപ്രകാരം ആകെ അവകാശവാദം രൂപ {amount}. <pauses> "
        "തുടരാൻ സ്ക്രീനിൽ Review and generate documents തിരഞ്ഞെടുക്കുക."
    ),
    "pa-IN": (
        "ਤੁਹਾਡਾ ਕਾਨੂੰਨੀ ਵਿਸ਼ਲੇਸ਼ਣ ਤਿਆਰ ਹੈ। <pauses> "
        "ਖਪਤਕਾਰ ਸੁਰੱਖਿਆ ਕਾਨੂੰਨ ਅਧੀਨ ਕੁੱਲ ਕਲੇਮ ਰੁਪਏ {amount} ਹੈ। <pauses> "
        "ਕਿਰਪਾ ਕਰਕੇ ਅੱਗੇ ਵਧਣ ਲਈ ਸਕ੍ਰੀਨ 'ਤੇ Review and generate documents ਚੁਣੋ।"
    ),
}

# 4. Progressive Single-Field Clarification Voice Prompts
SINGLE_FIELD_CLARIFICATION_TEMPLATES: dict[str, dict[str, str]] = {
    "full_name": {
        "hi-IN": (
            "Formal legal notice ke liye, <pauses> "
            "kripya apna poora kanooni naam batayein."
        ),
        "en-IN": (
            "To serve the formal legal demand, <pauses> "
            "please state your full legal name."
        ),
    },
    "order_id": {
        "hi-IN": (
            "Mamle ko verify karne ke liye, <pauses> "
            "apna Order ID, PNR, ya UPI UTR batayein."
        ),
        "en-IN": (
            "To link this dispute to the company records, <pauses> "
            "please provide your Order ID, booking PNR, or UPI reference."
        ),
    },
    "amount": {
        "hi-IN": (
            "Statutory damages calculate karne ke liye, <pauses> "
            "kripya batayein aapne kul kitne rupaye ada kiye the."
        ),
        "en-IN": (
            "To quantify statutory damages and interest, <pauses> "
            "please state the exact amount paid in Rupees."
        ),
    },
    "incident_date": {
        "hi-IN": (
            "Kanooni daawe ke record ke liye, <pauses> "
            "kripya batayein yeh mamla kis taareekh ko hua tha."
        ),
        "en-IN": (
            "For limitation and dispute evidence records, <pauses> "
            "on what date did this transaction or grievance occur?"
        ),
    },
    "brand": {
        "hi-IN": (
            "Statutory officer ko notice bhejne ke liye, <pauses> "
            "kripya company ya brand ka naam batayein."
        ),
        "en-IN": (
            "To address the statutory nodal grievance officer, <pauses> "
            "please state the company or brand name."
        ),
    },
}


class VoicePromptComposer:
    """Composes natural, tag-infused spoken prompts for Timbre v3.0."""

    @staticmethod
    def compose_welcome(language: str = "hi-IN") -> str:
        code = normalize_language_code(language)
        raw = WELCOME_VOICE_TEMPLATES.get(code, WELCOME_VOICE_TEMPLATES["hi-IN"])
        return sanitize_tags_for_tts(raw)

    @staticmethod
    def compose_single_field_clarification(field: str, language: str = "hi-IN") -> str:
        code = normalize_language_code(language)
        field_dict = SINGLE_FIELD_CLARIFICATION_TEMPLATES.get(field, {})
        if code == "en-IN":
            raw = field_dict.get("en-IN", CLARIFICATION_VOICE_TEMPLATES["en-IN"])
        else:
            raw = field_dict.get("hi-IN", CLARIFICATION_VOICE_TEMPLATES.get(code, CLARIFICATION_VOICE_TEMPLATES["hi-IN"]))
        return sanitize_tags_for_tts(raw)

    @staticmethod
    def compose_clarification(
        language: str = "hi-IN",
        missing_fields: list[str] | None = None,
        target_field: str | None = None,
    ) -> str:
        code = normalize_language_code(language)
        field = target_field
        if not field and missing_fields:
            for candidate in ["full_name", "order_id", "amount", "incident_date", "brand"]:
                if candidate in missing_fields:
                    field = candidate
                    break
            if not field and missing_fields:
                field = missing_fields[0]

        if field and field in SINGLE_FIELD_CLARIFICATION_TEMPLATES:
            return VoicePromptComposer.compose_single_field_clarification(field, code)

        raw = CLARIFICATION_VOICE_TEMPLATES.get(code, CLARIFICATION_VOICE_TEMPLATES["hi-IN"])
        return sanitize_tags_for_tts(raw)

    @staticmethod
    def compose_assessment(total_rupees: float | int, language: str = "hi-IN") -> str:
        code = normalize_language_code(language)
        template = ASSESSMENT_VOICE_TEMPLATES.get(code, ASSESSMENT_VOICE_TEMPLATES["hi-IN"])
        formatted_amount = f"{total_rupees:,.2f}"
        raw = template.format(amount=formatted_amount)
        return sanitize_tags_for_tts(raw)
