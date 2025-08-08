import time
import tempfile
from threading import Thread

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from werkzeug.serving import make_server

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
    assert (
        b'placeholder="Has\xc5\x82o"' in response.data
        or 'placeholder="Hasło"'.encode() in response.data
    )

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
    assert (
        b'Zmiana has\xc5\x82a' in response.data
        or 'Zmiana hasła'.encode() in response.data
    )
    assert (
        b'placeholder="Obecne has\xc5\x82o"' in response.data
        or 'placeholder="Obecne hasło"'.encode() in response.data
    )


@pytest.fixture
def live_server(app):
    server = make_server("127.0.0.1", 5001, app)
    thread = Thread(target=server.serve_forever)
    thread.start()
    time.sleep(1)
    yield "http://127.0.0.1:5001"
    server.shutdown()
    thread.join()


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    profile = tempfile.mkdtemp(prefix="chrome-profile-")
    options.add_argument(f"--user-data-dir={profile}")
    try:
        drv = webdriver.Chrome(options=options)
    except Exception as exc:
        pytest.skip(f"Chrome not available: {exc}")
    else:
        yield drv
        drv.quit()


def test_dark_mode_persists_after_refresh(live_server, driver):
    driver.get(live_server + "/")
    driver.find_element("id", "darkModeToggle").click()
    body = driver.find_element("tag name", "body")
    assert "dark-mode" in body.get_attribute("class")
    driver.refresh()
    body = driver.find_element("tag name", "body")
    assert "dark-mode" in body.get_attribute("class")


def test_select_search_filters_options(live_server, driver, login):
    login()  # ensure user exists
    driver.get(live_server + "/login")
    driver.find_element("name", "email").send_keys("test@example.com")
    driver.find_element("name", "password").send_keys("password")
    driver.find_element("css selector", "form button[type=submit]").click()

    driver.get(live_server + "/beneficjenci/nowy")
    container = driver.find_element("css selector", "#wojewodztwo + .choices")
    container.click()
    search_input = container.find_element("css selector", ".choices__input--cloned")
    assert search_input.get_attribute("aria-label") == "Wyszukaj"
    search_input.send_keys("Zach")
    time.sleep(0.5)
    visible = [
        el.text
        for el in container.find_elements(
            "css selector", ".choices__list--dropdown .choices__item--selectable"
        )
        if el.is_displayed()
    ]
    assert visible == ["Zachodniopomorskie"]

