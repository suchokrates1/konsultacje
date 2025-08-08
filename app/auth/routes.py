"""Authentication related view functions."""

import os
from urllib.parse import urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from .. import db
from ..utils import send_email
from ..forms import (
    LoginForm,
    RegisterForm,
    PasswordResetRequestForm,
    PasswordResetForm,
    UserSettingsForm,
)
from ..models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate a user and redirect to the next page."""
    next_url = request.args.get("next")
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.confirmed:
                flash("Twoje konto nie zostało jeszcze potwierdzone.")
                return render_template("login.html", form=form)
            login_user(user, remember=form.remember_me.data)
            if not next_url or urlparse(next_url).netloc != "":
                next_url = url_for("sessions.nowe_zajecia")
            return redirect(next_url)
        flash("Nieprawidłowe dane logowania.")
    return render_template("login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Create a new user account."""
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("Użytkownik z tym adresem email już istnieje.")
            return render_template("register.html", form=form)

        user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            confirmed=False,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        admin_cfg = current_app.config.get("MAIL_DEFAULT_SENDER")
        admin_email = os.environ.get("ADMIN_EMAIL")
        if isinstance(admin_cfg, tuple):
            admin_email = admin_cfg[1]
        elif admin_cfg:
            admin_email = admin_cfg
        if admin_email:
            token = user.get_confirm_token()
            confirm_url = url_for(
                "admin.admin_confirm_instruktora",
                user_id=user.id,
                token=token,
                _external=True,
            )
            body = (
                f"Użytkownik {user.full_name} zarejestrował się z adresem "
                f"{user.email}. Potwierdź konto: {confirm_url}"
            )
            html_body = render_template(
                "email/new_registration.html", confirm_url=confirm_url
            )
            _, status = send_email(
                "Nowa rejestracja użytkownika", [admin_email], body, html_body=html_body
            )
            if status == "error":
                flash("Nie udało się wysłać powiadomienia do administratora.")

        flash(
            "Rejestracja zakończona sukcesem. Poczekaj na potwierdzenie przez administratora."
        )
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    """Send a password reset link to the provided email address."""
    if current_user.is_authenticated:
        return redirect(url_for("sessions.index"))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            body = f"Kliknij link aby zresetować hasło: {reset_url}"
            _, status = send_email("Reset hasła", [user.email], body)
            if status == "error":
                flash("Nie udało się wysłać emaila z linkiem resetującym.")
        flash(
            "Jeśli podany email istnieje, wysłano instrukcje resetowania hasła."
        )
        return redirect(url_for("auth.login"))
    return render_template("reset_password_request.html", form=form)


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Allow the user to set a new password using a token."""
    if current_user.is_authenticated:
        return redirect(url_for("sessions.index"))
    user = User.verify_reset_token(token)
    if not user:
        flash("Link resetujący jest nieważny lub wygasł.")
        return redirect(url_for("auth.reset_password_request"))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Hasło zostało zresetowane.")
        return redirect(url_for("auth.login"))
    return render_template("reset_password.html", form=form)


@auth_bp.route("/settings", methods=["GET", "POST"])
@login_required
def user_settings():
    """Display and update user account settings."""
    form = UserSettingsForm()
    if form.validate_on_submit():
        current_user.email = form.email.data
        current_user.full_name = form.full_name.data
        current_user.default_duration = form.default_duration.data
        current_user.document_recipient_email = form.document_recipient_email.data
        current_user.session_type = form.session_type.data
        if form.new_password.data:
            if not current_user.check_password(form.old_password.data):
                flash("Nieprawidłowe aktualne hasło.")
                return render_template("settings.html", form=form)
            current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Ustawienia zapisane.")
        return redirect(url_for("auth.user_settings"))
    elif request.method == "GET":
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name
        form.default_duration.data = current_user.default_duration
        form.document_recipient_email.data = current_user.document_recipient_email
        form.session_type.data = current_user.session_type
    return render_template("settings.html", form=form)

