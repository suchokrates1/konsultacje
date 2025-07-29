import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from dotenv import load_dotenv

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'
mail = Mail()


def create_app():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    load_dotenv(env_path)
    app = Flask(__name__)
    # Flask 3 removed the `app.env` attribute. Use the configuration value
    # instead which is populated from the `FLASK_ENV` environment variable.
    env = app.config.get("ENV")
    secret_key = os.environ.get("SECRET_KEY")
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    admin_email = os.environ.get("ADMIN_EMAIL")
    if secret_key:
        app.config["SECRET_KEY"] = secret_key
    elif env == "development":
        # Provide a fallback key in development to avoid crashes if the
        # variable is not exported. A proper key should be configured for
        # production deployments.
        app.logger.warning(
            "SECRET_KEY not set, using insecure development key."
        )
        app.config["SECRET_KEY"] = "dev-secret-key"
    else:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Configure SECRET_KEY or run with FLASK_ENV=development."
        )

    # Ścieżka do bazy SQLite w katalogu 'instance'
    instance_path = os.path.join(app.root_path, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'konsultacje.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "localhost")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 25))
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "false").lower() == "true"
    app.config["MAIL_USE_SSL"] = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", admin_email)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    with app.app_context():
        from . import routes, models  # noqa: F401
        db.create_all()

        if admin_username and admin_password:
            from .models import User
            admin = User.query.filter_by(username=admin_username).first()
            if not admin:
                admin = User(username=admin_username, email=admin_email)
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()

    return app
