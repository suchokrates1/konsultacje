from datetime import date
from pathlib import Path
from types import SimpleNamespace

from flask import current_app

from app.utils import send_session_docx


def test_send_session_docx_sanitizes_specjalista(monkeypatch, app):
    paths = {}

    def fake_generate_docx(zajecia, beneficjenci, output_path):
        paths['path'] = output_path
        Path(output_path).write_bytes(b'dummy')

    def fake_send(msg):
        pass

    monkeypatch.setattr('app.utils.generate_docx', fake_generate_docx)
    monkeypatch.setattr('app.utils.mail.send', fake_send)

    with app.app_context():
        current_app.config['MAIL_DEFAULT_SENDER'] = 'sender@example.com'
        zajecia = SimpleNamespace(
            beneficjenci=[SimpleNamespace(imie='Ala')],
            data=date(2023, 1, 1),
            specjalista='Spec/Name',
        )
        send_session_docx(zajecia, 'dest@example.com')

    assert paths['path'].endswith('Konsultacje z Spec_Name 2023-01-01 Ala.docx')
