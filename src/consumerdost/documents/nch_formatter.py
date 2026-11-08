import urllib.parse
from consumerdost.domain.calculator import ClaimBreakdown, format_inr


NCH_WHATSAPP_NUMBER = "918860005372"
NCH_PORTAL_URL = "https://consumerhelpline.gov.in"


def format_nch_dossier(
    complainant_name: str,
    complainant_contact: str,
    brand_corporate_name: str,
    order_id: str,
    incident_date: str,
    category: str,
    claim: ClaimBreakdown,
    facts_summary: str,
) -> dict[str, str]:
    """Generate structured plain-text complaint block for National Consumer Helpline (NCH 1915).
    
    Returns dossier text (< 2,000 chars) and pre-filled WhatsApp deep link.
    """
    total_str = format_inr(claim.total_demanded_inr)
    principal_str = format_inr(claim.principal_inr)

    dossier_text = (
        "NATIONAL CONSUMER HELPLINE (NCH 1915 / INGRAM) GRIEVANCE FILING\n"
        "[DISCLAIMER: Automated assistance filing. Figures are indicative calculations for discussion. Not legal advice.]\n"
        "--------------------------------------------------\n"
        f"1. Complainant: {complainant_name} ({complainant_contact})\n"
        f"2. Respondent Brand: {brand_corporate_name}\n"
        f"3. Category: {category.replace('_', ' ').title()}\n"
        f"4. Order / Txn ID: {order_id}\n"
        f"5. Transaction Date: {incident_date}\n"
        f"6. Amount Disputed: {principal_str} (Illustrative Total Claim: {total_str})\n"
        f"7. Summary of Grievance:\n{facts_summary.strip()}\n"
        f"8. Statutory Relief Sought:\n100% refund of {principal_str} along with statutory interest "
        f"and damages for deficiency of service under Consumer Protection Act, 2019.\n"
        "--------------------------------------------------\n"
        "Generated via ConsumerDost Pre-Litigation Dispute Engine."
    )

    # Ensure length constraint
    if len(dossier_text) > 1950:
        dossier_text = dossier_text[:1940] + "\n..."

    # Create WhatsApp deep link
    encoded_text = urllib.parse.quote(dossier_text)
    whatsapp_url = f"https://wa.me/{NCH_WHATSAPP_NUMBER}?text={encoded_text}"

    return {
        "dossier_text": dossier_text,
        "whatsapp_url": whatsapp_url,
        "portal_url": NCH_PORTAL_URL,
    }
