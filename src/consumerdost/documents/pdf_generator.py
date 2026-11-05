from datetime import date
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from consumerdost.config import settings
from consumerdost.domain.calculator import ClaimBreakdown, format_inr
from consumerdost.domain.statutes import StatuteEntry


# Register TrueType fonts once
_FONTS_REGISTERED = False


def register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    regular_path = settings.fonts_dir / "NotoSans-Regular.ttf"
    bold_path = settings.fonts_dir / "NotoSans-Bold.ttf"

    if regular_path.exists() and bold_path.exists():
        pdfmetrics.registerFont(TTFont("NotoSans", str(regular_path)))
        pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(bold_path)))
        _FONTS_REGISTERED = True
    else:
        # Fallback to system fonts if assets dir missing
        sys_reg = Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf")
        sys_bold = Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf")
        if sys_reg.exists() and sys_bold.exists():
            pdfmetrics.registerFont(TTFont("NotoSans", str(sys_reg)))
            pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(sys_bold)))
            _FONTS_REGISTERED = True


class NumberedCanvas:
    """Two-pass canvas to add running footer with page numbers."""
    pass  # Standard canvas is sufficient for 1-2 page MVP


def generate_legal_notice_pdf(
    output_path: str | Path,
    case_reference_id: str,
    notice_date: date,
    complainant_name: str,
    complainant_contact: str,
    brand_corporate_name: str,
    registered_address: str,
    nodal_email: str,
    nodal_officer_name: str | None,
    order_id: str,
    incident_date: str,
    narrative_facts: str,
    statute_entry: StatuteEntry,
    claim: ClaimBreakdown,
    is_demo_mode: bool = False,
) -> Path:
    """Generate a formal Unicode-safe Legal Demand Notice PDF with native ₹ glyph support."""
    register_fonts()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    font_family = "NotoSans" if _FONTS_REGISTERED else "Helvetica"
    font_bold = "NotoSans-Bold" if _FONTS_REGISTERED else "Helvetica-Bold"

    doc = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        fontName=font_bold,
        fontSize=13,
        leading=16,
        alignment=1,  # Center
        textColor=colors.HexColor("#1A365D"),
    )
    header_style = ParagraphStyle(
        "HeaderMeta",
        fontName=font_bold,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2D3748"),
    )
    normal_style = ParagraphStyle(
        "DocNormal",
        fontName=font_family,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
    )
    bold_style = ParagraphStyle(
        "DocBold",
        fontName=font_bold,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1A202C"),
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        fontName=font_family,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#718096"),
        alignment=1,
    )

    elements = []

    # Demo Banner if applicable
    if is_demo_mode:
        demo_style = ParagraphStyle(
            "DemoBanner",
            fontName=font_bold,
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor("#C53030"),
        )
        elements.append(Paragraph("— HACKATHON DEMO SPECIMEN — FOR EVALUATION PURPOSES ONLY —", demo_style))
        elements.append(Spacer(1, 6))

    # Title
    elements.append(Paragraph("FORMAL LEGAL DEMAND NOTICE", title_style))
    elements.append(Paragraph("UNDER SECTION 35 OF THE CONSUMER PROTECTION ACT, 2019", ParagraphStyle(
        "SubTitle", fontName=font_bold, fontSize=10, leading=13, alignment=1, textColor=colors.HexColor("#4A5568")
    )))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=10))

    # Reference & Date Table
    ref_table_data = [
        [
            Paragraph(f"<b>Notice Ref:</b> {case_reference_id}", header_style),
            Paragraph(f"<b>Date:</b> {notice_date.strftime('%d %B %Y')}", header_style),
        ]
    ]
    ref_table = Table(ref_table_data, colWidths=[260, 255])
    ref_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(ref_table)
    elements.append(Spacer(1, 12))

    # Addressee & Complainant Blocks
    nodal_title = nodal_officer_name or "Nodal Grievance Redressal Officer"
    addr_text = f"""<b>TO:</b><br/>
{nodal_title}<br/>
<b>{brand_corporate_name}</b><br/>
{registered_address}<br/>
<b>Email:</b> {nodal_email}"""

    comp_text = f"""<b>FROM:</b><br/>
<b>{complainant_name}</b> (Complainant)<br/>
<b>Contact:</b> {complainant_contact}<br/>
<b>Order / Reference ID:</b> {order_id}<br/>
<b>Transaction Date:</b> {incident_date}"""

    party_table_data = [
        [Paragraph(addr_text, normal_style), Paragraph(comp_text, normal_style)]
    ]
    party_table = Table(party_table_data, colWidths=[260, 255])
    party_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 12))

    # Subject
    subj_text = f"<b>SUBJECT:</b> Formal Legal Demand for Redressal of Consumer Dispute concerning Order/Txn ID '{order_id}' for sum of {format_inr(claim.total_demanded_inr)}"
    elements.append(Paragraph(subj_text, bold_style))
    elements.append(Spacer(1, 10))

    # Statement of Facts
    elements.append(Paragraph("<b>1. STATEMENT OF FACTS</b>", bold_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(narrative_facts, normal_style))
    elements.append(Spacer(1, 10))

    # Statutory Violations
    elements.append(Paragraph("<b>2. STATUTORY VIOLATIONS CITED</b>", bold_style))
    elements.append(Spacer(1, 4))
    for sec in statute_entry.cpa_sections:
        elements.append(Paragraph(f"• <b>{sec}</b>", normal_style))
    for rule in statute_entry.sectoral_rules:
        elements.append(Paragraph(f"• {rule}", normal_style))
    elements.append(Spacer(1, 10))

    # Itemized Demand Table
    elements.append(Paragraph("<b>3. ITEMIZED FINANCIAL DEMAND & CLAIMS (PAISE PRECISION)</b>", bold_style))
    elements.append(Spacer(1, 4))

    claim_rows = [
        [Paragraph("<b>Claim Head</b>", bold_style), Paragraph("<b>Basis / Calculation</b>", bold_style), Paragraph("<b>Amount (INR)</b>", bold_style)],
        [Paragraph("Principal Consideration", normal_style), Paragraph("Refund of invoiced amount", normal_style), Paragraph(format_inr(claim.principal_inr), normal_style)],
        [Paragraph("Equitable Statutory Interest", normal_style), Paragraph(f"9% p.a. for {claim.days_elapsed} days", normal_style), Paragraph(format_inr(claim.interest_inr), normal_style)],
    ]
    if claim.statutory_penalty_paise > 0:
        claim_rows.append([
            Paragraph("Regulatory Penalty / Compensation", normal_style),
            Paragraph("Mandated under RBI/DGCA sectoral provisions", normal_style),
            Paragraph(format_inr(claim.statutory_penalty_inr), normal_style),
        ])
    claim_rows.append([
        Paragraph("Mental Agony & Harassment", normal_style),
        Paragraph("Tiered compensation for operational stonewalling", normal_style),
        Paragraph(format_inr(claim.damages_inr), normal_style),
    ])
    claim_rows.append([
        Paragraph("<b>TOTAL DEMANDED</b>", bold_style),
        Paragraph("<b>Payable within 7 Calendar Days</b>", bold_style),
        Paragraph(f"<b>{format_inr(claim.total_demanded_inr)}</b>", bold_style),
    ])

    claim_table = Table(claim_rows, colWidths=[170, 215, 130])
    claim_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(claim_table)
    elements.append(Spacer(1, 10))

    # Warning / Compliance Window
    elements.append(Paragraph("<b>4. NOTICE PERIOD & JURISDICTIONAL WARNING</b>", bold_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(statute_entry.statutory_warning, normal_style))
    elements.append(Spacer(1, 14))

    # Signature Block
    sig_text = f"Sincerely,<br/><br/><b>{complainant_name}</b><br/>Complainant (Self-Represented)"
    elements.append(Paragraph(sig_text, normal_style))
    elements.append(Spacer(1, 14))

    # Footer Disclaimer
    disclaimer = (
        "<b>STATUTORY DISCLAIMER (CPA 2019 SECTION 35):</b> This legal notice is generated by ConsumerDost as a "
        "pre-litigation self-representation drafting engine pursuant to Section 35 of the Consumer Protection Act, 2019, "
        "which statutory provision empowers Indian citizens to represent themselves before consumer redressal authorities. "
        "This notice does not constitute unauthorized practice of law or licensed advocacy."
    )
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=6))
    elements.append(Paragraph(disclaimer, disclaimer_style))

    doc.build(elements)
    return output_file
