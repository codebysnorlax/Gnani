from consumerdost.agent.state import ConsumerDostState
from consumerdost.domain.calculator import format_inr


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
        f"• 9% p.a. Equitable Interest: {format_inr(interest_inr)}",
    ]
    if statutory_inr > 0:
        breakdown_lines.append(f"• Sectoral Penalty (RBI/DGCA): {format_inr(statutory_inr)}")
    breakdown_lines.append(f"• Harassment & Agony Damages: {format_inr(damages_inr)}")

    breakdown_text = "\n".join(breakdown_lines)

    return (
        f"📋 <b>Pre-Litigation Case Assessment Ready ({case_ref})</b>\n\n"
        f"👤 <b>Complainant:</b> {complainant} ({contact})\n"
        f"🏢 <b>Corporate Entity:</b> {corporate_name}\n"
        f"📧 <b>Nodal Officer:</b> {nodal_title} ({nodal_email})\n"
        f"🔢 <b>Order / Txn ID:</b> <code>{order_id}</code> | <b>Date:</b> {incident_date}\n\n"
        f"⚖️ <b>Applicable Statutory Provisions:</b>\n{clauses_preview}\n\n"
        f"💰 <b>Itemized Claim Breakdown:</b>\n{breakdown_text}\n"
        f"👉 <b>Total Legal Demand:</b> <b>{format_inr(total_inr)}</b>\n\n"
        f"⏳ <b>Statutory Compliance Window:</b> 7 Calendar Days\n\n"
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
