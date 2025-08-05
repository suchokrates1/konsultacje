from flask_mail import Message
from app import send_email


def test_send_email_uses_thread(monkeypatch, app):
    calls = []

    def fake_async(app_obj, msg):
        calls.append(msg)

    monkeypatch.setattr('app.send_async_email', fake_async)

    started = {'value': False}

    class DummyThread:
        def __init__(self, target, args=()):
            assert target is fake_async
            self.target = target
            self.args = args
        def start(self):
            started['value'] = True
            self.target(*self.args)

    monkeypatch.setattr('app.Thread', DummyThread)

    with app.app_context():
        msg = Message('sub', recipients=['x@example.com'])
        send_email(msg)

    assert started['value']
    assert calls and calls[0].recipients == ['x@example.com']
