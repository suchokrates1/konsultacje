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
   The `flask` command will load variables from this file automatically
   and an admin user will be created if it does not exist.
3. (Optional) Run in development mode:
   ```bash
   export FLASK_ENV=development
   flask --app run.py run
   ```
   In production you **must** provide a real `SECRET_KEY` in `.env`.
4. Start the application normally:
   ```bash
   flask --app run.py run
   ```

## Docker

You can build and run the project in a container:

```bash
docker build -t konsultacje .
docker run --env-file .env -p 8080:5000 konsultacje
```

Alternatively run `docker-compose up` to use the provided compose file which exposes the app on port `8080`.
