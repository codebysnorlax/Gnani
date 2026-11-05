import tempfile
from datetime import date
from pathlib import Path
from pypdf import PdfReader

from consumerdost.documents.pdf_generator import generate_legal_notice_pdf
from consumerdost.domain.calculator import calculate_claim
from consumerdost.domain.statutes import get_statute_entry


def test_pdf_unicode_and_content_integrity():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / "test_notice.pdf"

        claim = calculate_claim(
            amount_paid_inr=14999.00,
            incident_date=date(2026, 10, 25),
            notice_date=date(2026, 11, 3),
            issue_type="ECOMMERCE_DEFECTIVE_GOODS",
        )
        statute = get_statute_entry("ECOMMERCE_DEFECTIVE_GOODS")

        out = generate_legal_notice_pdf(
            output_path=pdf_path,
            case_reference_id="CD-2026-0042",
            notice_date=date(2026, 11, 3),
            complainant_name="Rohan Sharma",
            complainant_contact="rohan@example.com / +91 9876543210",
            brand_corporate_name="Flipkart Internet Private Limited",
            registered_address="Buildings Alyssa, Embassy Tech Village, Bengaluru - 560103",
            nodal_email="grievance.officer@flipkart.com",
            nodal_officer_name="Grievance Redressal Officer",
            order_id="OD3091823901",
            incident_date="2026-10-25",
            narrative_facts="Delivered mobile phone with broken screen; return refused.",
            statute_entry=statute,
            claim=claim,
            is_demo_mode=True,
        )

        assert out.exists()
        assert out.stat().st_size > 0

        # Read PDF text using pypdf
        reader = PdfReader(str(out))
        assert len(reader.pages) >= 1
        full_text = "".join(page.extract_text() or "" for page in reader.pages)

        # 1. Assert ₹ symbol is present and clean (no black box / ■)
        assert "₹" in full_text
        assert "■" not in full_text

        # 2. Assert key legal facts and parties
        assert "CD-2026-0042" in full_text
        assert "Flipkart Internet Private Limited" in full_text
        assert "grievance.officer@flipkart.com" in full_text
        assert "Rohan Sharma" in full_text
        assert "OD3091823901" in full_text
        assert "Section 35" in full_text
        assert "Section 2(10)" in full_text
