import io
import os
from datetime import datetime
from PIL import Image
from app.services.reports import sanitize_csv_cell, generate_complaints_csv, generate_complaints_pdf, generate_single_complaint_docket_pdf
from app.services.evidence import validate_file_content, save_evidence_file
from app.models import Report, User, Evidence
from app import db
from werkzeug.datastructures import FileStorage


def test_csv_formula_injection_defense():
    """Verify formula injection characters are escaped by prepending single quote."""
    dangerous_inputs = [
        "=cmd|' /C calc'!A0",
        "+cmd|' /C calc'!A0",
        "-cmd|' /C calc'!A0",
        "@SUM(A1:A10)",
        "\tmalicious_tab",
        "\rmalicious_return"
    ]
    for inp in dangerous_inputs:
        sanitized = sanitize_csv_cell(inp)
        assert sanitized.startswith("'"), f"Failed to sanitize: {inp}"

    # Safe text remains unaffected
    assert sanitize_csv_cell("Normal Text 123") == "Normal Text 123"
    assert sanitize_csv_cell("") == ""
    assert sanitize_csv_cell(None) == ""


def test_evidence_file_content_validation():
    """Verify MIME and magic byte validation for images and PDFs."""
    # 1. Valid PNG Image
    img_io = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='blue')
    image.save(img_io, format='PNG')
    img_io.seek(0)

    valid_file = FileStorage(stream=img_io, filename='test_proof.png', content_type='image/png')
    is_valid, msg = validate_file_content(valid_file)
    assert is_valid is True

    # 2. Fake PDF (wrong header bytes)
    fake_pdf = FileStorage(stream=io.BytesIO(b'NOT A REAL PDF FILE'), filename='fake.pdf', content_type='application/pdf')
    is_valid_pdf, msg_pdf = validate_file_content(fake_pdf)
    assert is_valid_pdf is False
    assert "Invalid PDF" in msg_pdf

    # 3. Disallowed extension (.exe / .sh)
    bad_ext = FileStorage(stream=io.BytesIO(b'binary code'), filename='virus.exe', content_type='application/x-msdownload')
    is_valid_bad, msg_bad = validate_file_content(bad_ext)
    assert is_valid_bad is False


def test_pdf_generation_without_errors(app):
    """Ensure reportlab PDF generator builds valid PDF binary streams."""
    with app.app_context():
        c1 = User.query.filter_by(username='test_citizen').first()
        rep = Report(
            complaint_number='CS-2026-777001',
            user_id=c1.id,
            title='PDF Generation Test Docket',
            description='Testing reportlab compilation for CivicShield AI.',
            crime_category='Theft',
            incident_date=datetime(2026, 11, 18, 10, 0),
            district='Central District',
            incident_location='Main Street',
            police_station='City Police Station',
            status='Under Investigation'
        )
        db.session.add(rep)
        db.session.commit()

        # Generate summary PDF
        pdf_summary = generate_complaints_pdf([rep])
        assert pdf_summary.getvalue().startswith(b'%PDF')

        # Generate single docket PDF
        pdf_docket = generate_single_complaint_docket_pdf(rep)
        assert pdf_docket.getvalue().startswith(b'%PDF')
