import time
from threading import Thread
import tempfile

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from werkzeug.serving import make_server

from app import db
from app.models import User


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


def test_login_mobile_view(live_server, driver):
    driver.set_window_size(375, 812)
    driver.get(live_server + "/login")
    scroll = driver.execute_script(
        "return document.documentElement.scrollWidth > window.innerWidth"
    )
    assert not scroll


def test_beneficjenci_mobile_view(app, live_server, driver):
    with app.app_context():
        user = User(full_name="mob", email="m@b.com")
        user.set_password("pass")
        user.confirmed = True
        db.session.add(user)
        db.session.commit()
    driver.set_window_size(375, 812)
    driver.get(live_server + "/login")
    driver.find_element("name", "full_name").send_keys("mob")
    driver.find_element("name", "password").send_keys("pass")
    driver.find_element("css selector", "button[type=submit]").click()
    driver.get(live_server + "/beneficjenci")
    scroll = driver.execute_script(
        "return document.documentElement.scrollWidth > window.innerWidth"
    )
    assert not scroll


