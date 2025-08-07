import pytest

def test_flash_message_displayed(client, app):
    # Przykład: sprawdź czy komunikat flash pojawia się po rejestracji
    response = client.post('/register', data={
        'full_name': 'Test User',
        'email': 'test-flash@example.com',
        'password': 'password',
        'confirm': 'password'
    }, follow_redirects=True)
    assert b'konto' in response.data or b'potwierdzenie' in response.data

def test_login_form_placeholders(client):
    response = client.get('/login')
    assert b'placeholder="adres@email.pl"' in response.data
    assert b'placeholder="Has\xc5\x82o"' in response.data or b'placeholder="Hasło"' in response.data

def test_dark_mode_toggle_button(client):
    response = client.get('/')
    # Sprawdź czy przycisk przełączania trybu ciemnego jest obecny
    assert b'id="darkModeToggle"' in response.data

def test_register_form_autocomplete(client):
    response = client.get('/register')
    assert b'autocomplete="email"' in response.data
    assert b'autocomplete="name"' in response.data

def test_settings_form_password_section(client, auth):
    # Zaloguj się i przejdź do ustawień
    auth.login()
    response = client.get('/settings')
    assert b'Zmiana has\xc5\x82a' in response.data or b'Zmiana hasła' in response.data
    assert b'placeholder="Obecne has\xc5\x82o"' in response.data or b'placeholder="Obecne hasło"' in response.data
