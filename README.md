# Konsultacje Application

A small Flask application that lets specialists register sessions with beneficiaries and produce printable DOCX reports. The project stores data using SQLite and provides a simple web interface secured with Flask‑Login.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   The `email_validator` package is included in `requirements.txt` and must
   be installed for form validation to work correctly. The file now also
   lists `python-docx` which is used to generate DOCX reports.
2. Copy `.env.example` to `.env` and set values for `SECRET_KEY`,
   `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_EMAIL`.
   A secure `SECRET_KEY` is required in **all** environments and there is
   no automatic fallback. You can generate one with:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   Configure email delivery with `MAIL_SERVER`, `MAIL_PORT`,
   `MAIL_USERNAME`, `MAIL_PASSWORD`, and optionally `MAIL_USE_TLS`
   or `MAIL_USE_SSL` for encrypted connections.
   The `flask` command will load variables from this file automatically
   and an admin user will be created if it does not exist.
3. Initialize the migration directory (first run only):
   ```bash
   flask --app run.py db init
   flask --app run.py db migrate -m "initial"
   flask --app run.py db upgrade
   ```
4. (Optional) Run in development mode:
   ```bash
    export FLASK_ENV=development
    flask --app run.py run
    ```
   The application will fail to start if `SECRET_KEY` is missing.
5. Start the application normally:
   ```bash
   flask --app run.py run
   ```
6. Report generation uses the `wzor.docx` template filled with session data
   and saves the result as a DOCX file.

## DOCX reports

The `app/docx_generator.py` module renders session details into the
`static/wzor.docx` template using **python-docx**. From the session list view
you can click **Pobierz raport** to hit the `/zajecia/<id>/docx` endpoint which
generates the document, serves it for download, and cleans up the temporary
file afterwards.

## Creating a user

Before logging in for the first time you must add at least one account. Launch a
Python shell with Flask context and create the user manually:

```bash
flask shell
>>> from app import db, models
>>> u = models.User(full_name="admin", email="admin@example.com")
>>> u.set_password("password")
>>> db.session.add(u); db.session.commit()
```

## Docker

You can build and run the project in a container:

```bash
docker build -t konsultacje .
docker run --env-file .env -p 8080:5000 konsultacje
```

Alternatively run `docker-compose up` to use the provided compose file which exposes the app on port `8080`.

## Running tests

The project uses **pytest** for the test suite located in `tests/`. Install the
runtime dependencies along with the developer tools from `requirements-dev.txt`, then run:

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

`requirements-dev.txt` also includes **flake8** for optional style checks.
This will create a temporary SQLite database in the `instance/` folder while the tests run. Each test passes a `SECRET_KEY` directly to `create_app`. If you add more tests, ensure `SECRET_KEY` is supplied via the configuration or environment.

## Best practices

- Przed wprowadzeniem zmian utwórz nową gałąź (`git checkout -b feature/nazwa-funkcji`).
- Stosuj czytelne komunikaty commitów i opisuj zmiany.
- Przeglądaj kod pod kątem powtarzających się fragmentów – przenoś je do funkcji lub modułów pomocniczych.
- Regularnie uruchamiaj testy automatyczne przed wypchnięciem zmian.

## Development workflow

1. Sklonuj repozytorium i zainstaluj zależności.
2. Pracuj na osobnej gałęzi.
3. Przed commitem uruchom testy (`pytest`).
4. Po zakończeniu pracy wykonaj code review (samodzielnie lub w zespole).
5. Po akceptacji scalaj do głównej gałęzi (`main` lub `master`).

## Testing

- Testy znajdują się w katalogu `tests/`.
- Do uruchamiania testów używaj `pytest`.
- Dodawaj nowe testy dla każdej nowej funkcji lub poprawki błędu.
- Przykład uruchomienia testów:
  ```bash
  pytest
  ```
- Jeśli dodajesz nową funkcjonalność, napisz testy jednostkowe i integracyjne.

## Dependencies update

- Regularnie aktualizuj zależności w `requirements.txt` i `requirements-dev.txt`.
- Sprawdzaj nowe wersje np. Bootstrap, python-docx, Flask.
- Po aktualizacji zależności uruchom testy, aby upewnić się, że wszystko działa poprawnie.
- Przykład aktualizacji pakietu:
  ```bash
  pip install --upgrade python-docx
  pip freeze > requirements.txt
  ```

## Code style

- Stosuj PEP8 (możesz użyć `flake8` do sprawdzenia stylu).
- Unikaj powielania kodu – korzystaj z funkcji pomocniczych i dziedziczenia.
- Komentuj fragmenty wymagające wyjaśnienia.
- Nazwy zmiennych i funkcji powinny być czytelne i opisowe.

## Refaktoryzacja backendu

- Jeśli zauważysz powtarzające się fragmenty kodu (np. obsługa formularzy, walidacja, generowanie raportów), przenieś je do osobnych funkcji lub modułów.
- Przykład: funkcje do obsługi flash messages, generowania raportów, wysyłki maili – patrz `app/utils.py`.
- Rozważ użycie blueprintów Flask do lepszej organizacji kodu.
- Przykład refaktoryzacji:
  ```python
  # app/utils.py
  from flask import flash

  def flash_success(message):
      flash(message, 'success')

  def flash_error(message):
      flash(message, 'danger')
  ```
  Następnie w widokach:
  ```python
  from app.utils import flash_success, flash_error

  # ...w kodzie...
  flash_success("Operacja zakończona sukcesem!")
  flash_error("Wystąpił błąd.")
  ```

- Do renderowania pól formularzy używaj makra z `app/templates/_form_macros.html`:
  ```html
  {% from '_form_macros.html' import render_field %}
  {{ render_field(form.email, 'adres@email.pl') }}
  ```

- W testach korzystaj z fixture do logowania (`tests/conftest.py`):
  ```python
  def test_dashboard_access(client, login):
      login()
      response = client.get('/dashboard')
      assert response.status_code == 200
  ```

## Aktualizacja zależności frontendowych

- Aby zaktualizować Bootstrap lub inne zależności frontendowe, zaktualizuj linki CDN w `base.html` lub zainstaluj nowszą wersję przez npm/yarn, jeśli korzystasz z bundlera.
- Po aktualizacji sprawdź wygląd aplikacji i uruchom testy.

## Przykładowy szablon testu automatycznego

- Przykład testu dla rejestracji użytkownika (`tests/test_auth.py`):
  ```python
  def test_register(client):
      response = client.post('/register', data={
          'full_name': 'Test User',
          'email': 'test@example.com',
          'password': 'password',
          'confirm': 'password'
      }, follow_redirects=True)
      assert b'konto' in response.data
  ```
