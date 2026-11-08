"""Empathetic voice prompt composer with Timbre v3.0 inline audio tags for all 10 Indic languages."""

import logging
from typing import Any
from consumerdost.speech.gnani_tts import normalize_language_code

logger = logging.getLogger(__name__)

# 1. Onboarding / Welcome Spoken Prompts with Timbre v3.0 Audio Tags
WELCOME_VOICE_TEMPLATES: dict[str, str] = {
    "hi-IN": (
        "Namaste! <excited> Main hoon ConsumerDost. <pauses> "
        "Aapka consumer dispute sunkar turant legal notice aur consumer helpline filing taiyaar karunga. "
        "<slow> Kripya ek voice note bhej kar batayein aapke saath kya hua."
    ),
    "en-IN": (
        "Hello! <excited> I am ConsumerDost. <pauses> "
        "I will convert your consumer grievance into a formal legal notice and consumer helpline dossier. "
        "<slow> Please send a voice note describing what happened."
    ),
    "kn-IN": (
        "ನಮಸ್ಕಾರ! <excited> ನಾನು ಕನ್ಸ್ಯೂಮರ್ ದೋಸ್ತ್. <pauses> "
        "ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ಆಲಿಸಿ ಲೀಗಲ್ ನೋಟಿಸ್ ಮತ್ತು ಹೆಲ್ಪ್‌ಲೈನ್ ದೂರು ಸಿದ್ಧಪಡಿಸುತ್ತೇನೆ. "
        "<slow> ದಯವಿಟ್ಟು ಧ್ವನಿ ಸಂದೇಶ ಕಳುಹಿಸಿ."
    ),
    "ta-IN": (
        "வணக்கம்! <excited> நான் கன்ஸ்யூமர் தோஸ்த். <pauses> "
        "உங்கள் நுகர்வோர் புகாரைக் கேட்டு சட்ட அறிவிப்பு மற்றும் உதவி மையக் கோப்பை உருவாக்குவேன். "
        "<slow> உங்கள் குரல் பதிவை அனுப்புங்கள்."
    ),
    "te-IN": (
        "నమస్కారం! <excited> నేను కన్స్యూమర్ దోస్త్. <pauses> "
        "మీ సమస్యను విని లీగల్ నోటీసు మరియు హెల్ప్‌లైన్ ఫిర్యాదును సిద్ధం చేస్తాను. "
        "<slow> దయచేసి మీ వాయిస్ నోట్ పంపండి."
    ),
    "mr-IN": (
        "नमस्कार! <excited> मी ग्राहक दोस्त आहे. <pauses> "
        "तुमची तक्रार ऐकून त्वरित कायदेशीर नोटीस आणि तक्रार अर्ज तयार करेन. "
        "<slow> कृपया व्हॉइस नोट पाठवा."
    ),
    "bn-IN": (
        "নমস্কার! <excited> আমি কনজিউমার দোস্ত। <pauses> "
        "আপনার অভিযোগ শুনে আইনি নোটিশ এবং হেল্পলাইন ফাইল প্রস্তুত করব। "
        "<slow> দয়া করে একটি ভয়েস বার্তা পাঠান।"
    ),
    "gu-IN": (
        "નમસ્તે! <excited> હું કન્ઝ્યુમર દોસ્ત છું. <pauses> "
        "તમારી ગ્રાહક ફરિયાદ સાંભળીને કાનૂની નોટિસ તૈયાર કરીશ. "
        "<slow> કૃપા કરીને તમારો વૉઇસ સંદેશ મોકલો."
    ),
    "ml-IN": (
        "നമസ്കാരം! <excited> ഞാൻ കൺസ്യൂമർ ദോസ്ത്. <pauses> "
        "നിങ്ങളുടെ പരാതി കേട്ട് നിയമപരമായ നോട്ടീസ് തയ്യാറാക്കാം. "
        "<slow> ദയവായി ഒരു വോയ്‌സ് നോട്ട് അയക്കൂ."
    ),
    "pa-IN": (
        "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! <excited> ਮੈਂ ਹਾਂ ਕੰਜ਼ਿਊਮਰ ਦੋਸਤ। <pauses> "
        "ਤੁਹਾਡੀ ਸ਼ਿਕਾਇਤ ਸੁਣ ਕੇ ਕਾਨੂੰਨੀ ਨੋਟਿਸ ਤਿਆਰ ਕਰਾਂਗਾ। "
        "<slow> ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਵੌਇਸ ਨੋਟ ਭੇਜੋ।"
    ),
}

# 2. Clarification Voice Prompts with Empathetic Audio Tags
CLARIFICATION_VOICE_TEMPLATES: dict[str, str] = {
    "hi-IN": (
        "<sigh> Brand ne aapko kafi pareshan kiya hai. <pauses> "
        "<slow> Legal notice complete karne ke liye kuch jankari chahiye. "
        "<whispers> Kripya apna Order ID, Transaction UTR, ya apna poora naam batayein."
    ),
    "en-IN": (
        "<sigh> It looks like the vendor caused you significant distress. <pauses> "
        "<slow> To finalize the statutory demand notice, I need a few more details. "
        "<whispers> Please provide your Order ID, Transaction UTR, or your full legal name."
    ),
    "kn-IN": (
        "<sigh> ಕಂಪನಿಯು ನಿಮಗೆ ತೊಂದರೆ ಉಂಟುಮಾಡಿದೆ. <pauses> "
        "<slow> ಕಾನೂನು ನೋಟಿಸ್ ಪೂರ್ಣಗೊಳಿಸಲು ವಿವರಗಳು ಬೇಕಾಗಿವೆ. "
        "<whispers> ದಯವಿಟ್ಟು ನಿಮ್ಮ ಆರ್ಡರ್ ಐಡಿ ಅಥವಾ ಪೂರ್ಣ ಹೆಸರನ್ನು ತಿಳಿಸಿ."
    ),
    "ta-IN": (
        "<sigh> நிறுவனம் உங்களுக்கு அநீதி இழைத்துள்ளது. <pauses> "
        "<slow> சட்ட அறிவிப்பை முடிக்க விவரங்கள் தேவை. "
        "<whispers> உங்கள் ஆர்டர் ஐடி அல்லது முழுப் பெயரைத் தெரிவிக்கவும்."
    ),
    "te-IN": (
        "<sigh> కంపెనీ మిమ్మల్ని ఇబ్బంది పెట్టింది. <pauses> "
        "<slow> చట్టపరమైన నోటీసు కోసం మరికొన్ని వివరాలు అవసరం. "
        "<whispers> దయచేసి మీ ఆర్డర్ ఐడీ లేదా పూర్తి పేరును తెలియజేయండి."
    ),
    "mr-IN": (
        "<sigh> कंपनीने तुम्हाला खूप त्रास दिला आहे. <pauses> "
        "<slow> कायदेशीर नोटीससाठी थोडी अधिक माहिती हवी आहे. "
        "<whispers> कृपया तुमचा ऑर्डर आयडी किंवा पूर्ण नाव सांगा."
    ),
    "bn-IN": (
        "<sigh> কোম্পানি আপনাকে হয়রানি করেছে। <pauses> "
        "<slow> আইনি নোটিশ তৈরি করতে কিছু অতিরিক্ত তথ্য প্রয়োজন। "
        "<whispers> অনুগ্রহ করে আপনার অর্ডার আইডি বা নাম বলুন।"
    ),
    "gu-IN": (
        "<sigh> કંપનીએ તમને ઘણી હેરાનગતિ કરી છે. <pauses> "
        "<slow> કાનૂની નોટિસ માટે કેટલીક વિગતોની જરૂર છે. "
        "<whispers> કૃપા કરીને તમારો ઓર્ડર આઈડી અથવા પૂરું નામ જણાવો."
    ),
    "ml-IN": (
        "<sigh> കമ്പനി നിങ്ങളെ ബുദ്ധിമുട്ടിച്ചു. <pauses> "
        "<slow> നിയമപരമായ നോട്ടീസിനായി കൂടുതൽ വിവരങ്ങൾ ആവശ്യമുണ്ട്. "
        "<whispers> ദയവായി ഓർഡർ ഐഡിയോ പേരോ നൽകുക."
    ),
    "pa-IN": (
        "<sigh> ਕੰਪਨੀ ਨੇ ਤੁਹਾਨੂੰ ਬਹੁਤ ਪ੍ਰੇਸ਼ਾਨ ਕੀਤਾ ਹੈ। <pauses> "
        "<slow> ਕਾਨੂੰਨੀ ਨੋਟਿਸ ਲਈ ਕੁਝ ਹੋਰ ਜਾਣਕਾਰੀ ਚਾਹੀਦੀ ਹੈ। "
        "<whispers> ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਆਰਡਰ ਆਈਡੀ ਜਾਂ ਪੂਰਾ ਨਾਮ ਦੱਸੋ।"
    ),
}

# 3. Assessment Walkthrough Voice Prompts
ASSESSMENT_VOICE_TEMPLATES: dict[str, str] = {
    "hi-IN": (
        "<excited> Aapka legal claim analysis taiyaar hai! <pauses> "
        "Consumer Protection Act 2019 ke tehat kul daawa banta hai rupaye {amount}. <pauses> "
        "<slow> Brand Nodal Officer ke khilaf 15-day notice window taiyaar hai. "
        "<pauses> Kripya dhyan dein, yeh sanketik ganana hai, kanooni salah nahi. "
        "Kripya screen par confirmation button dabayein."
    ),
    "en-IN": (
        "<excited> Your legal dispute analysis is ready! <pauses> "
        "Under the Consumer Protection Act 2019, your total quantified claim is Rupees {amount}. <pauses> "
        "<slow> A formal 15-day pre-litigation demand notice is drafted. "
        "<pauses> Please note, these figures are indicative calculations, not formal legal advice. "
        "Please tap the confirm button on your screen."
    ),
    "kn-IN": (
        "<excited> ನಿಮ್ಮ ಕಾನೂನು ವಿಶ್ಲೇಷಣೆ ಸಿದ್ಧವಾಗಿದೆ! <pauses> "
        "ಗ್ರಾಹಕ ಸಂರಕ್ಷಣಾ ಕಾಯ್ದೆಯಡಿ ಒಟ್ಟು ಹಕ್ಕು ಮೊತ್ತ ರೂಪಾಯಿ {amount}. <pauses> "
        "<slow> ಅಧಿಕೃತ ನೋಟಿಸ್ ಸಿದ್ಧಪಡಿಸಲಾಗಿದೆ. "
        "<pauses> <slow> ಇದು ಚರ್ಚೆಗಾಗಿ ಸಾಂಕೇತಿಕ ಲೆಕ್ಕಾಚಾರ, ಕಾನೂನು ಸಲಹೆಯಲ್ಲ. "
        "ದಯವಿಟ್ಟು ಸ್ಕ್ರೀನ್‌ನಲ್ಲಿ ದೃಢೀಕರಿಸಿ."
    ),
    "ta-IN": (
        "<excited> உங்கள் சட்ட ஆய்வு தயாராக உள்ளது! <pauses> "
        "நுகர்வோர் பாதுகாப்புச் சட்டத்தின் கீழ் மொத்தக் கோரிக்கை ரூபாய் {amount}. <pauses> "
        "<slow> அதிகாரப்பூர்வ அறிவிப்பு தயாராக உள்ளது. "
        "<pauses> <slow> இது கலந்துரையாடலுக்கான உத்தேச கணக்கீடே, சட்ட ஆலோசனை அல்ல. "
        "திரையில் உறுதிப்படுத்தவும்."
    ),
    "te-IN": (
        "<excited> మీ చట్టపరమైన విశ్లేషణ సిద్ధంగా ఉంది! <pauses> "
        "వినియోగదారుల రక్షణ చట్టం ప్రకారం మొత్తం క్లెయిమ్ రూపాయలు {amount}. <pauses> "
        "<slow> అధికారిక నోటీసు సిద్ధమైంది. "
        "<pauses> <slow> ఇది చర్చల కోసం సూచిక లెక్క మాత్రమే, చట్టపరమైన సలహా కాదు. "
        "దయచేసి స్క్రీన్‌పై నిర్ధారించండి."
    ),
    "mr-IN": (
        "<excited> तुमचे कायदेशीर विश्लेषण तयार आहे! <pauses> "
        "ग्राहक संरक्षण कायद्यानुसार एकूण मागणी रुपये {amount} आहे. <pauses> "
        "<slow> अधिकृत नोटीस तयार आहे. "
        "<pauses> <slow> ही आकडेवारी चर्चेसाठी सांकेतिक गणना आहे, कायदेशीर सल्ला नाही. "
        "कृपया स्क्रीनवर पुष्टी करा."
    ),
    "bn-IN": (
        "<excited> আপনার আইনি বিশ্লেষণ প্রস্তুত! <pauses> "
        "ভোক্তা সুরক্ষা আইনের অধীনে মোট দাবি টাকা {amount}। <pauses> "
        "<slow> আইনি নোটিশ তৈরি করা হয়েছে। "
        "<pauses> <slow> এটি আলোচনার জন্য নির্দেশক হিসাব, আইনি পরামর্শ নয়। "
        "অনুগ্রহ করে স্ক্রিনে নিশ্চিত করুন।"
    ),
    "gu-IN": (
        "<excited> તમારું કાનૂની વિશ્લેષણ તૈયાર છે! <pauses> "
        "ગ્રાહક સુરક્ષા કાયદા હેઠળ કુલ દાવો રૂપિયા {amount} થાય છે. <pauses> "
        "<slow> સત્તાવાર નોટિસ તૈયાર છે. "
        "<pauses> <slow> આ આંકડા ચર્ચા માટે માત્ર સૂચક ગણતરી છે, કાનૂની સલાહ નથી. "
        "કૃપા કરીને સ્ક્રીન પર પુષ્ટિ કરો."
    ),
    "ml-IN": (
        "<excited> നിങ്ങളുടെ നിയമപരമായ വിശകലനം തയ്യാറാണ്! <pauses> "
        "ഉപഭോക്തൃ സംരക്ഷണ നിയമപ്രകാരം ആകെ അവകാശവാദം രൂപ {amount}. <pauses> "
        "<slow> നോട്ടീസ് തയ്യാറാണ്. "
        "<pauses> <slow> ഇത് ചർച്ചകൾക്കുള്ള സൂചക കണക്കുകൂട്ടൽ മാത്രമാണ്, നിയമോപദേശമല്ല. "
        "ദയവായി സ്ക്രീനിൽ സ്ഥിരീകരിക്കുക."
    ),
    "pa-IN": (
        "<excited> ਤੁਹਾਡਾ ਕਾਨੂੰਨੀ ਵਿਸ਼ਲੇਸ਼ਣ ਤਿਆਰ ਹੈ! <pauses> "
        "ਖਪਤਕਾਰ ਸੁਰੱਖਿਆ ਕਾਨੂੰਨ ਅਧੀਨ ਕੁੱਲ ਕਲੇਮ ਰੁਪਏ {amount} ਹੈ। <pauses> "
        "<slow> ਕਾਨੂੰਨੀ ਨੋਟਿਸ ਤਿਆਰ ਹੈ। "
        "<pauses> <slow> ਇਹ ਅੰਕੜੇ ਚਰਚਾ ਲਈ ਸੰਕੇਤਕ ਗਣਨਾ ਹਨ, ਕਾਨੂੰਨੀ ਸਲਾਹ ਨਹੀਂ। "
        "ਕਿਰਪਾ ਕਰਕੇ ਸਕ੍ਰੀਨ 'ਤੇ ਪੁਸ਼ਟੀ ਕਰੋ।"
    ),
}

# 4. Progressive Single-Field Clarification Voice Prompts with Timbre v3.0 Audio Tags
SINGLE_FIELD_CLARIFICATION_TEMPLATES: dict[str, dict[str, str]] = {
    "full_name": {
        "hi-IN": (
            "<sigh> Brand ne aapko kafi pareshan kiya hai. <pauses> "
            "<slow> Formal legal notice bhejne ke liye, <whispers> kripya apna poora kanooni naam batayein."
        ),
        "en-IN": (
            "<sigh> It looks like the vendor caused you significant distress. <pauses> "
            "<slow> To serve the formal legal demand, <whispers> please state your full legal name."
        ),
    },
    "order_id": {
        "hi-IN": (
            "<sigh> Kripya dhyan dein. <pauses> "
            "<slow> Mamle ko verify karne ke liye, <whispers> apna Order ID, PNR, ya UPI UTR batayein."
        ),
        "en-IN": (
            "<sigh> To link this dispute to the company records, <pauses> "
            "<slow> <whispers> Please provide your exact Order ID, booking PNR, or 12-digit UPI UTR."
        ),
    },
    "amount": {
        "hi-IN": (
            "<slow> Statutory damages calculate karne ke liye, <pauses> "
            "<whispers> kripya batayein aapne kul kitne rupaye ada kiye the."
        ),
        "en-IN": (
            "<slow> To quantify statutory damages and interest, <pauses> "
            "<whispers> please state the exact amount paid in Rupees."
        ),
    },
    "incident_date": {
        "hi-IN": (
            "<slow> Kanooni daawe ke record ke liye, <pauses> "
            "<whispers> kripya batayein yeh mamla kis taareekh ko hua tha."
        ),
        "en-IN": (
            "<slow> For limitation and dispute evidence records, <pauses> "
            "<whispers> on what date did this transaction or grievance occur?"
        ),
    },
    "brand": {
        "hi-IN": (
            "<slow> Statutory officer ko notice bhejne ke liye, <pauses> "
            "<whispers> kripya company ya brand ka naam batayein."
        ),
        "en-IN": (
            "<slow> To address the statutory nodal grievance officer, <pauses> "
            "<whispers> please state the company or brand name."
        ),
    },
}


class VoicePromptComposer:
    """Composes empathetic, tag-infused spoken prompts for Timbre v3.0."""

    @staticmethod
    def compose_welcome(language: str = "hi-IN") -> str:
        code = normalize_language_code(language)
        return WELCOME_VOICE_TEMPLATES.get(code, WELCOME_VOICE_TEMPLATES["hi-IN"])

    @staticmethod
    def compose_single_field_clarification(field: str, language: str = "hi-IN") -> str:
        """Compose targeted single-field voice clarification with empathetic Timbre audio tags."""
        code = normalize_language_code(language)
        field_dict = SINGLE_FIELD_CLARIFICATION_TEMPLATES.get(field, {})
        if code == "en-IN":
            return field_dict.get("en-IN", CLARIFICATION_VOICE_TEMPLATES["en-IN"])
        return field_dict.get("hi-IN", CLARIFICATION_VOICE_TEMPLATES.get(code, CLARIFICATION_VOICE_TEMPLATES["hi-IN"]))

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

        return CLARIFICATION_VOICE_TEMPLATES.get(code, CLARIFICATION_VOICE_TEMPLATES["hi-IN"])

    @staticmethod
    def compose_assessment(total_rupees: float | int, language: str = "hi-IN") -> str:
        code = normalize_language_code(language)
        template = ASSESSMENT_VOICE_TEMPLATES.get(code, ASSESSMENT_VOICE_TEMPLATES["hi-IN"])
        formatted_amount = f"{total_rupees:,.2f}"
        return template.format(amount=formatted_amount)

