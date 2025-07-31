# Konsultacje Application

A small Flask application that lets specialists register sessions with beneficiaries and produce printable PDF reports. The project stores data using SQLite and provides a simple web interface secured with Flask‑Login.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set values for `SECRET_KEY`,
   `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_EMAIL`.
   A secure `SECRET_KEY` is required in **all** environments. You can
   generate one with:

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

## Creating a user

Before logging in for the first time you must add at least one account. Launch a
Python shell with Flask context and create the user manually:

```bash
flask shell
>>> from app import db, models
>>> u = models.User(username="admin", email="admin@example.com")
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

The project uses **pytest** for the test suite located in `tests/`. Install the dependencies and pytest, then run:

```bash
pip install -r requirements.txt pytest
pytest
```

This will create a temporary SQLite database in the `instance/` folder while the tests run.
