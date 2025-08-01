"""Flask application factory and extension initialization."""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from dotenv import load_dotenv

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'
mail = Mail()
csrf = CSRFProtect()


def create_app(test_config=None):
    """Create and configure the Flask application.

    The function loads environment variables, initializes extensions and
    registers application blueprints. A database and an optional admin user are
    created on the first run.

    Parameters
    ----------
    test_config: dict | None
        Optional configuration values used during testing.

    Returns
    -------
    Flask
        The configured Flask application instance.
    """
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)
    app = Flask(__name__)
    # Flask loads configuration from environment variables such as `FLASK_ENV`.
    secret_key = None
    if test_config is not None:
        secret_key = test_config.get("SECRET_KEY")

    if not secret_key:
        secret_key = os.environ.get("SECRET_KEY")

    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    admin_email = os.environ.get("ADMIN_EMAIL")

    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY must be provided via environment or configuration."
        )

    app.config["SECRET_KEY"] = secret_key

    if test_config:
        app.config.update(test_config)

    # Ścieżka do bazy SQLite w katalogu 'instance'
    instance_path = os.path.join(app.root_path, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'konsultacje.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    mail_server = os.environ.get("MAIL_SERVER", "localhost")
    mail_port = int(os.environ.get("MAIL_PORT", 25))
    mail_username = os.environ.get("MAIL_USERNAME")
    mail_password = os.environ.get("MAIL_PASSWORD")
    mail_use_tls = os.environ.get("MAIL_USE_TLS", "false").lower() == "true"
    mail_use_ssl = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    app.config.update(
        MAIL_SERVER=mail_server,
        MAIL_PORT=mail_port,
        MAIL_USERNAME=mail_username,
        MAIL_PASSWORD=mail_password,
        MAIL_USE_TLS=mail_use_tls,
        MAIL_USE_SSL=mail_use_ssl,
        MAIL_DEFAULT_SENDER=os.environ.get("MAIL_DEFAULT_SENDER", admin_email),
    )

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    Migrate(app, db)

    with app.app_context():
        from . import routes, models  # noqa: F401
        from flask_migrate import upgrade
        upgrade()

        if admin_username and admin_password:
            from .models import User, Roles
            admin = User.query.filter_by(full_name=admin_username).first()
            if not admin:
                admin = User(
                    full_name=admin_username,
                    email=admin_email,
                    role=Roles.ADMIN,
                )
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()

    return app
