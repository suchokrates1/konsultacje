"""Tests ensuring generated DOCX files contain the expected text."""

import os
from datetime import date, time
from docx import Document

from app import db
from app.models import User, Beneficjent, Zajecia
from app.docx_generator import generate_docx


def _docx_text(doc: Document) -> str:
    """Extract all text content from a DOCX document."""

    text = "\n".join(p.text for p in doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text += "\n" + cell.text
    return text


def test_generate_docx_file_contains_text(app, tmp_path):
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

        path = tmp_path / "report.docx"
        generate_docx(zajecia, [benef], str(path))
        doc = Document(str(path))
        text = _docx_text(doc)
        assert "disk" in text
        assert "Tomek" in text
        assert "dietetykiem" not in text

        template = Document(os.path.join(app.root_path, "static", "wzor.docx"))
        assert "dietetykiem" in _docx_text(template)
