"""Tests ensuring generated PDF files contain the expected text."""

from datetime import date, time
import os
import tempfile

from pypdf import PdfReader
from docx import Document
import app.pdf_generator as pdfgen


def _create_pdf(text, path):
    """Write a minimal PDF containing *text* used for testing."""
    text = text.replace('(', '\\(').replace(')', '\\)')
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 12 Tf 50 800 Td ({text}) Tj ET"
    encoded = stream.encode('latin-1', 'ignore')
    objects.append(f"<< /Length {len(encoded)} >>\nstream\n{stream}\nendstream")
    content = ['%PDF-1.4']
    offsets = []
    offset = len(content[0]) + 1
    for i, obj in enumerate(objects, start=1):
        offsets.append(offset)
        part = f"{i} 0 obj\n{obj}\nendobj"
        content.append(part)
        offset += len(part) + 1
    xref_offset = offset
    xref = ["xref", f"0 {len(objects)+1}", "0000000000 65535 f "]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n ")
    content.append("\n".join(xref))
    content.append(f"trailer\n<< /Root 1 0 R /Size {len(objects)+1} >>")
    content.append(f"startxref\n{xref_offset}")
    content.append("%%EOF")
    with open(path, 'wb') as f:
        f.write("\n".join(content).encode('latin-1', 'ignore'))


def fake_convert(docx_path, pdf_path):
    from flask import current_app
    ctx = current_app.config.get("_last_pdf_context", {})
    text = " \n".join(str(v) for v in ctx.values())
    _create_pdf(text, pdf_path)

from app import db
from app.models import User, Beneficjent, Zajecia
from app.pdf_generator import generate_pdf


def test_generate_pdf_file_contains_text(app, monkeypatch):
    """PDF generated on disk should include rendered session data."""

    monkeypatch.setattr(pdfgen, "convert", fake_convert)

    with app.app_context():
        user = User(full_name="disk", email="disk@example.com")
        user.set_password("pass")
        user.confirmed = True
        db.session.add(user)
        db.session.commit()

        benef = Beneficjent(imie="Tomek", wojewodztwo="Mazowieckie", user_id=user.id)
        db.session.add(benef)
        zajecia = Zajecia(
            data=date(2023, 3, 3),
            godzina_od=time(10, 0),
            godzina_do=time(11, 0),
            specjalista="disk",
            user_id=user.id,
        )
        zajecia.beneficjenci.append(benef)
        db.session.add(zajecia)
        db.session.commit()

        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        try:
            generate_pdf(zajecia, [benef], path)
            reader = PdfReader(path)
            text = "".join(page.extract_text() or "" for page in reader.pages)
            assert "disk" in text
            assert "Tomek" in text
        finally:
            os.remove(path)

