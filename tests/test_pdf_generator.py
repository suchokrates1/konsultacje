"""Tests ensuring generated PDF files contain the expected text."""

from datetime import date, time
import os
import tempfile

from pypdf import PdfReader

from app import db
from app.models import User, Beneficjent, Zajecia
from app.pdf_generator import generate_pdf


def test_generate_pdf_file_contains_text(app):
    """PDF generated on disk should include overlayed session data."""

    with app.app_context():
        user = User(full_name="disk", email="disk@example.com")
        user.set_password("pass")
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

