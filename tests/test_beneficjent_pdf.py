"""Tests for beneficiary CRUD operations and PDF generation."""

from datetime import date, time
import io
import os

from app import db
from app.models import User, Beneficjent, Zajecia
from pypdf import PdfReader
from docx import Document
import app.pdf_generator as pdfgen


def _create_pdf(text, path):
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


def create_user(app):
    """Create a user in the database and return its ID."""

    with app.app_context():
        user = User(full_name='tester', email='tester@example.com')
        user.set_password('secret')
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, username='tester', password='secret'):
    """Log in a user using the test client."""

    return client.post(
        '/login',
        data={'full_name': username, 'password': password},
        follow_redirects=True,
    )


def test_beneficjent_crud(app, client):
    """Add, edit and delete a beneficiary through the web interface."""

    create_user(app)
    login(client)

    # Verify dropdown renders
    resp = client.get('/beneficjenci/nowy')
    html = resp.get_data(as_text=True)
    assert '<select' in html
    assert html.count('<option') >= 16

    # Add
    response = client.post(
        '/beneficjenci/nowy',
        data={'imie': 'Jan Kowalski', 'wojewodztwo': 'Mazowieckie'},
        follow_redirects=True,
    )
    assert 'Beneficjent dodany' in response.get_data(as_text=True)
    with app.app_context():
        benef = Beneficjent.query.filter_by(imie='Jan Kowalski').first()
        assert benef is not None
        benef_id = benef.id

    # Edit
    response = client.post(
        f'/beneficjenci/{benef_id}/edytuj',
        data={'imie': 'Jan Nowak', 'wojewodztwo': 'Slaskie'},
        follow_redirects=True,
    )
    assert 'Beneficjent zaktualizowany' in response.get_data(as_text=True)
    with app.app_context():
        benef = db.session.get(Beneficjent, benef_id)
        assert benef.imie == 'Jan Nowak'
        assert benef.wojewodztwo == 'Slaskie'

    # Delete
    response = client.post(
        f'/beneficjenci/{benef_id}/usun',
        data={'submit': '1'},
        follow_redirects=True,
    )
    assert 'Beneficjent usunięty' in response.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Beneficjent, benef_id) is None


def test_create_session(app, client):
    """Create a consultation session and verify it was stored."""
    user_id = create_user(app)
    login(client)
    with app.app_context():
        benef = Beneficjent(
            imie='Anna', wojewodztwo='Pomorskie', user_id=user_id
        )
        db.session.add(benef)
        db.session.commit()
        b_id = benef.id

    response = client.post(
        '/zajecia/nowe',
        data={
            'data': '2023-01-01',
            'godzina_od': '10:00',
            'godzina_do': '11:00',
            'beneficjenci': str(b_id),
        },
        follow_redirects=True,
    )
    assert response.request.path == '/zajecia'
    assert 'Zajęcia zapisane' in response.get_data(as_text=True)
    with app.app_context():
        zajecia = Zajecia.query.filter_by(user_id=user_id).first()
        assert zajecia is not None
        assert len(zajecia.beneficjenci) == 1


def test_pdf_generation(app, client, monkeypatch):
    """Generate a PDF report and ensure the file is removed afterwards."""
    monkeypatch.setattr(pdfgen, "convert", fake_convert)
    user_id = create_user(app)
    login(client)
    with app.app_context():
        benef = Beneficjent(
            imie='Piotr', wojewodztwo='Lubelskie', user_id=user_id
        )
        db.session.add(benef)
        zajecia = Zajecia(
            data=date(2023, 1, 2),
            godzina_od=time(9, 0),
            godzina_do=time(10, 0),
            specjalista='tester',
            user_id=user_id
        )
        zajecia.beneficjenci.append(benef)
        db.session.add(zajecia)
        db.session.commit()
        z_id = zajecia.id

    response = client.get(f'/zajecia/{z_id}/pdf')
    assert response.status_code == 200
    assert 'application/pdf' in response.headers.get('Content-Type', '')
    disposition = response.headers.get('Content-Disposition', '')
    expected_name = (
        "Konsultacje dietetyczne 2023-01-02 Piotr.pdf"
    )
    assert disposition.startswith('attachment')
    assert expected_name in disposition

    pdf_path = os.path.join(
        app.root_path,
        'static',
        'pdf',
        expected_name,
    )
    # the generated PDF should be removed after the response is sent
    assert not os.path.exists(pdf_path)


def test_pdf_content(app, client, monkeypatch):
    """Generate a PDF and verify expected text appears in the document."""
    monkeypatch.setattr(pdfgen, "convert", fake_convert)
    user_id = create_user(app)
    login(client)
    with app.app_context():
        benef = Beneficjent(
            imie="Katarzyna", wojewodztwo="Mazowieckie", user_id=user_id
        )
        db.session.add(benef)
        zajecia = Zajecia(
            data=date(2023, 2, 1),
            godzina_od=time(8, 0),
            godzina_do=time(9, 0),
            specjalista="tester",
            user_id=user_id,
        )
        zajecia.beneficjenci.append(benef)
        db.session.add(zajecia)
        db.session.commit()
        z_id = zajecia.id

    response = client.get(f"/zajecia/{z_id}/pdf")
    assert response.status_code == 200

    reader = PdfReader(io.BytesIO(response.data))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    assert "tester" in text
    assert "Katarzyna" in text
    assert "Mazowieckie" in text
