# Konsultacje Application

A small Flask application that lets specialists register sessions with beneficiaries and produce printable PDF reports. The project stores data using SQLite and provides a simple web interface secured with Flask‑Login.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Export a `SECRET_KEY` environment variable when deploying to production. If it
   is missing and `FLASK_ENV=development`, a fallback key will be used.
3. Run the application in development mode without setting `SECRET_KEY`:
   ```bash
   export FLASK_ENV=development
   flask --app run.py run
   ```
   In production you **must** define `SECRET_KEY` before starting the
   application.
4. Start the application normally:
   ```bash
   flask --app run.py run
   ```

## Docker

You can build and run the project in a container:

```bash
docker build -t konsultacje .
docker run -e SECRET_KEY=your-secret -p 8080:5000 konsultacje
```

Alternatively run `docker-compose up` to use the provided compose file which exposes the app on port `8080`.
