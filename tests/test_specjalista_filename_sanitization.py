from datetime import date
from types import SimpleNamespace

from app.utils import send_session_docx


def test_send_session_docx_sanitizes_specjalista(monkeypatch, app):
    captured = {}

    def fake_generate_docx(zajecia, beneficjenci, output):
        output.write(b'dummy')

    def fake_send_email(subject, recipients, body, attachments=None):
        captured['attachments'] = attachments
        return None, 'sent'

    monkeypatch.setattr('app.utils.generate_docx', fake_generate_docx)
    monkeypatch.setattr('app.utils.send_email', fake_send_email)

    with app.app_context():
        zajecia = SimpleNamespace(
            beneficjenci=[SimpleNamespace(imie='Ala')],
            data=date(2023, 1, 1),
            specjalista='Spec/Name',
        )
        send_session_docx(zajecia, 'dest@example.com')

    filename = captured['attachments'][0][0]
    assert filename == 'Konsultacje z Spec_Name 2023-01-01 Ala.docx'
