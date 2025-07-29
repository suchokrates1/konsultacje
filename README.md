# Konsultacje Application

This Flask application allows specialists to manage sessions and generate PDF reports for beneficiaries.

## Environment Variables

- `SECRET_KEY` – secret key used by Flask for session management and CSRF protection.
  In development (`FLASK_ENV=development`), the application falls back to a built‑in
  development key if this variable isn't defined. In other environments the variable
  must be provided.

