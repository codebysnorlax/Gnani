from consumerdost.agent.state import ConsumerDostState
from consumerdost.domain.calculator import format_inr
from consumerdost.speech.gnani_tts import normalize_language_code

MULTILINGUAL_DISCLAIMERS: dict[str, str] = {
    "en-IN": "This is an automated assistance tool. Figures are indicative calculations for discussion with the brand and NCH. This is not legal advice.",
    "hi-IN": "यह एक स्वचालित सहायता उपकरण है। आंकड़े ब्रांड और एनसीएच के साथ चर्चा के लिए सांकेतिक गणना हैं। यह कानूनी सलाह नहीं है।",
    "kn-IN": "ಇದು ಸ್ವಯಂಚಾಲಿತ ನೆರವು ಸಾಧನವಾಗಿದೆ. ಅಂಕಿಅಂಶಗಳು ಬ್ರ್ಯಾಂಡ್ ಮತ್ತು NCH ನೊಂದಿಗೆ ಚರ್ಚೆಗಾಗಿ ಸಾಂಕೇತಿಕ ಲೆಕ್ಕಾಚಾರಗಳಾಗಿವೆ. ಇದು ಕಾನೂನು ಸಲಹೆಯಲ್ಲ.",
    "ta-IN": "இது ஒரு தானியங்கி உதவி கருவியாகும். புள்ளிவிவரங்கள் பிராண்ட் மற்றும் NCH உடன் கலந்துரையாடுவதற்கான உத்தேச கணக்கீடுகள் மட்டுமே. இது சட்ட ஆலோசனை அல்ல.",
    "te-IN": "ఇది ఆటోమేటెడ్ సహాయ సాధనం. గణాంకాలు బ్రాండ్ మరియు NCHతో చర్చించడానికి సూచిక లెక్కలు మాత్రమే. ఇది చట్టపరమైన సలహా కాదు.",
    "mr-IN": "हे एक स्वयंचलित सहाय्य साधन आहे. आकडेवारी ब्रँड आणि एनसीएचशी चर्चेसाठी केवळ सांकेतिक गणना आहेत. हा कायदेशीर सल्ला नाही.",
    "bn-IN": "এটি একটি স্বয়ংক্রিয় সহায়তা সরঞ্জাম। পরিসংখ্যানগুলি ব্র্যান্ড এবং এনসিএইচের সাথে আলোচনার জন্য নির্দেশক গণনা। এটি আইনি পরামর্শ নয়।",
    "gu-IN": "આ એક સ્વચાલિત સહાયક સાધન છે. આંકડા બ્રાન્ડ અને NCH સાથે ચર્ચા માટે માત્ર સૂચક ગણતરી છે. આ કાનૂની સલાહ નથી.",
    "ml-IN": "ഇതൊരു ഓട്ടോമേറ്റഡ് സഹായ ഉപകരണമാണ്. കണക്കുകൾ ബ്രാൻഡും എൻസിഎച്ചുമായി ചർച്ച ചെയ്യുന്നതിനുള്ള സൂചക കണക്കുകൂട്ടലുകൾ മാത്രമാണ്. ഇത് നിയമോപദേശമല്ല.",
    "pa-IN": "ਇਹ ਇੱਕ ਸਵੈਚਾਲਿਤ ਸਹਾਇਤਾ ਟੂਲ ਹੈ। ਅੰਕੜੇ ਬ੍ਰਾਂਡ ਅਤੇ ਐਨਸੀਐਚ ਨਾਲ ਚਰਚਾ ਲਈ ਸਿਰਫ਼ ਸੰਕੇਤਕ ਗਣਨਾ ਹਨ। ਇਹ ਕਾਨੂੰਨੀ ਸਲਾਹ ਨਹੀਂ ਹੈ।",
}


def get_legal_disclaimer(language: str = "hi-IN") -> str:
    """Retrieve statutory disclaimer for specified Indic language."""
    code = normalize_language_code(language)
    return MULTILINGUAL_DISCLAIMERS.get(code, MULTILINGUAL_DISCLAIMERS["hi-IN"])


def format_welcome_message() -> str:
    return (
        "⚖️ <b>ConsumerDost (उपभोक्ता दोस्त)</b>\n"
        "<i>AI-Powered Voice Consumer Rights & Pre-Litigation Dispute Engine</i>\n\n"
        "Speak or type your consumer grievance in Hindi, Hinglish, or English. "
        "We turn your complaint into a complete, legally grounded <b>Tri-Fold Escalation Dossier</b> "
        "in seconds:\n\n"
        "1. 📄 <b>Formal Legal Demand Notice (PDF)</b> with copyable Nodal Officer email\n"
        "2. 💬 <b>National Consumer Helpline (NCH 1915)</b> 1-tap WhatsApp submission\n"
        "3. 🐦 <b>Public Social Escalation Draft</b> for X (Twitter)\n"
        "4. 🎙️ <b>Gnani.ai Indic Voice Summary</b> explaining your next steps\n\n"
        "🔒 <b>Privacy Pledge:</b> Banking passwords, PINs, OTPs, and card numbers are "
        "automatically redacted. Only transaction IDs and public grievance facts are processed.\n\n"
        "📜 <b>Statutory Notice:</b> ConsumerDost is an automated self-representation drafting engine "
        "under Section 35 of the Consumer Protection Act, 2019. It does not provide licensed advocacy.\n\n"
        "👇 <b>Tap a sample grievance below or send a voice note now to start:</b>"
    )


def format_assessment_card(state: ConsumerDostState) -> str:
    brand_info = state.get("brand_resolved") or {}
    corporate_name = brand_info.get("corporate_name", state.get("brand_raw", "Respondent Brand"))
    nodal_email = brand_info.get("nodal_email", "Not Found")
    nodal_title = brand_info.get("nodal_officer_name") or "Grievance Redressal Officer"

    order_id = state.get("order_id") or "N/A"
    incident_date = state.get("incident_date") or "N/A"
    complainant = state.get("complainant_full_name") or "Valued Consumer"
    contact = state.get("complainant_contact") or "Provided in Case"
    case_ref = state.get("case_reference_id") or "CD-2026-DRAFT"

    principal_inr = (state.get("principal_paise") or 0) / 100.0
    interest_inr = (state.get("calculated_interest_paise") or 0) / 100.0
    statutory_inr = (state.get("statutory_penalty_paise") or 0) / 100.0
    damages_inr = (state.get("damages_claimed_paise") or 0) / 100.0
    total_inr = (state.get("total_claim_paise") or 0) / 100.0

    clauses = state.get("legal_clauses") or [
        "Section 2(10) of CPA 2019 (Defect in Goods)",
        "Section 2(11) of CPA 2019 (Deficiency in Service)",
    ]
    clauses_preview = "\n".join(f"• {c}" for c in clauses[:3])

    breakdown_lines = [
        f"• Principal Refund: {format_inr(principal_inr)}",
        f"• 18% p.a. Statutory Interest: {format_inr(interest_inr)}",
    ]
    if statutory_inr > 0:
        breakdown_lines.append(f"• Sectoral Penalty (RBI/DGCA): {format_inr(statutory_inr)}")
    breakdown_lines.append(f"• Harassment & Agony Damages: {format_inr(damages_inr)}")

    breakdown_text = "\n".join(breakdown_lines)
    lang = state.get("preferred_language", "hi-IN")
    disclaimer = get_legal_disclaimer(lang)

    stt_ms = state.get("stt_latency_ms")
    tts_ms = state.get("tts_latency_ms")
    latency_info = []
    if stt_ms is not None:
        latency_info.append(f"STT: {stt_ms}ms")
    if tts_ms is not None:
        latency_info.append(f"TTS: {tts_ms}ms")
    latency_suffix = f" ({', '.join(latency_info)})" if latency_info else ""

    return (
        f"📋 <b>Pre-Litigation Case Assessment Ready ({case_ref})</b>\n\n"
        f"👤 <b>Complainant:</b> {complainant} ({contact})\n"
        f"🏢 <b>Corporate Entity:</b> {corporate_name}\n"
        f"📧 <b>Nodal Officer:</b> {nodal_title} ({nodal_email})\n"
        f"🔢 <b>Order / Txn ID:</b> <code>{order_id}</code> | <b>Date:</b> {incident_date}\n\n"
        f"⚖️ <b>Applicable Statutory Provisions:</b>\n{clauses_preview}\n\n"
        f"💰 <b>Itemized Claim Breakdown:</b>\n{breakdown_text}\n"
        f"👉 <b>Illustrative Pre-Litigation Demand Estimate:</b> <b>{format_inr(total_inr)}</b>\n\n"
        f"⏳ <b>Statutory Compliance Window:</b> 7–15 Calendar Days\n\n"
        f"⚠️ <i><b>Disclaimer:</b> {disclaimer}</i>\n\n"
        f"⚡ <i>Powered by Gnani Prisma v3.0 + Timbre v3.0{latency_suffix}</i>\n\n"
        f"<i>Tap below to generate your complete PDF Legal Notice and escalation package.</i>"
    )


def format_cover_email(state: ConsumerDostState) -> str:
    brand_info = state.get("brand_resolved") or {}
    nodal_email = brand_info.get("nodal_email", "")
    corporate_name = brand_info.get("corporate_name", "Vendor")
    order_id = state.get("order_id", "N/A")
    case_ref = state.get("case_reference_id", "")
    complainant = state.get("complainant_full_name", "Consumer")
    contact = state.get("complainant_contact", "")

    total_inr = (state.get("total_claim_paise") or 0) / 100.0

    return (
        f"<b>📧 Copy-Paste Nodal Officer Email Block:</b>\n\n"
        f"<b>To:</b> <code>{nodal_email}</code>\n"
        f"<b>Subject:</b> <code>LEGAL DEMAND NOTICE: {order_id} - Ref {case_ref} - {corporate_name}</code>\n\n"
        f"<b>Body:</b>\n"
        f"<pre>"
        f"Dear Nodal Grievance Redressal Officer,\n\n"
        f"Please find attached the formal Legal Demand Notice under Section 35 of the "
        f"Consumer Protection Act, 2019 regarding Order/Transaction ID '{order_id}'.\n\n"
        f"Total Claim Demanded: {format_inr(total_inr)}.\n"
        f"Compliance Timeline: 7 Calendar Days.\n\n"
        f"Failure to resolve this grievance will compel filing of petition before the competent "
        f"District Consumer Disputes Redressal Commission (DCDRC).\n\n"
        f"Sincerely,\n"
        f"{complainant}\n"
        f"{contact}\n"
        f"</pre>"
    )


def format_next_steps_card(state: ConsumerDostState) -> str:
    brand_info = state.get("brand_resolved") or {}
    nodal_email = brand_info.get("nodal_email", "support@brand.com")
    case_ref = state.get("case_reference_id", "CD-2026")
    lang = state.get("preferred_language", "hi-IN")
    disclaimer = get_legal_disclaimer(lang)

    return (
        f"🎯 <b>What to Do Next — Escalation Roadmap ({case_ref})</b>\n\n"
        f"<b>Step 1: Direct Corporate Notice (Email)</b>\n"
        f"• Email the attached PDF Legal Notice to: <code>{nodal_email}</code>\n"
        f"• Allow 7–15 calendar days statutory compliance window.\n\n"
        f"<b>Step 2: National Consumer Helpline 1915 (Day 8)</b>\n"
        f"• If unresolved, submit Document 2 to the official NCH 1915 WhatsApp bot.\n\n"
        f"<b>Step 3: Public Accountability (X / Social)</b>\n"
        f"• Post Document 3 on X tagging the brand and @jagograhakjago.\n\n"
        f"⚠️ <i><b>Disclaimer:</b> {disclaimer}</i>\n\n"
        f"⚡ <i>Powered by Gnani Prisma v3.0 + Timbre v3.0</i>"
    )
