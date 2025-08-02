"""Tests ensuring generated DOCX files contain the expected text."""

from datetime import date, time
import os
import tempfile

from docx import Document

from app import db
from app.models import User, Beneficjent, Zajecia
from app.docx_generator import generate_docx


def test_generate_docx_file_contains_text(app):
    """DOCX generated on disk should include rendered session data."""

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

        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            generate_docx(zajecia, [benef], path)
            doc = Document(path)
            text = "\n".join(p.text for p in doc.paragraphs)
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += "\n" + cell.text
            assert "disk" in text
            assert "Tomek" in text
        finally:
            os.remove(path)
