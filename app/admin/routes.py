"""Administrative view functions and utilities."""

import os
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from wtforms.validators import ValidationError

from .. import db, mail
from ..utils import send_email
from ..forms import (
    BeneficjentForm,
    ConfirmForm,
    DeleteForm,
    PromoteForm,
    SettingsForm,
    UserEditForm,
    ZajeciaForm,
)
from ..models import Beneficjent, Roles, Settings, User, Zajecia


admin_bp = Blueprint("admin", __name__)


def admin_required(view_func):
    """Decorate ``view_func`` to allow access only for admin users."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if (
            not current_user.is_authenticated
            or current_user.role != Roles.ADMIN
        ):
            return abort(403)
        return view_func(*args, **kwargs)

    return wrapper


@admin_bp.route("/beneficjenci")
@login_required
@admin_required
def admin_beneficjenci():
    """Show all beneficiaries to the admin user."""
    beneficjenci = Beneficjent.query.all()
    delete_form = DeleteForm()
    return render_template(
        "admin/beneficjenci_list.html",
        beneficjenci=beneficjenci,
        delete_form=delete_form,
    )


@admin_bp.route("/beneficjenci/<int:beneficjent_id>/edytuj", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edytuj_beneficjenta(beneficjent_id):
    """Admin view for editing any beneficiary."""
    benef = Beneficjent.query.get_or_404(beneficjent_id)
    form = BeneficjentForm(obj=benef)
    if form.validate_on_submit():
        benef.imie = form.imie.data
        benef.wojewodztwo = form.wojewodztwo.data
        db.session.commit()
        flash("Beneficjent zaktualizowany.")
        return redirect(url_for("admin.admin_beneficjenci"))
    return render_template(
        "beneficjent_form.html", form=form, title="Edytuj beneficjenta"
    )


@admin_bp.route("/beneficjenci/<int:beneficjent_id>/usun", methods=["POST"])
@login_required
@admin_required
def admin_usun_beneficjenta(beneficjent_id):
    """Admin action to delete a beneficiary."""
    form = DeleteForm()
    if form.validate_on_submit():
        benef = Beneficjent.query.get_or_404(beneficjent_id)
        db.session.delete(benef)
        db.session.commit()
        flash("Beneficjent usunięty.")
    return redirect(url_for("admin.admin_beneficjenci"))


@admin_bp.route("/zajecia")
@login_required
@admin_required
def admin_zajecia():
    """Display all sessions for the admin."""
    zajecia_list = Zajecia.query.order_by(
        Zajecia.data.desc(), Zajecia.godzina_od.desc()
    ).all()
    delete_form = DeleteForm()
    return render_template(
        "admin/zajecia_list.html",
        zajecia_list=zajecia_list,
        delete_form=delete_form,
    )


@admin_bp.route("/zajecia/<int:zajecia_id>/edytuj", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edytuj_zajecia(zajecia_id):
    """Admin view for editing any session."""
    zajecia = Zajecia.query.get_or_404(zajecia_id)
    form = ZajeciaForm(obj=zajecia)
    form.beneficjenci.choices = [
        (b.id, f"{b.imie} ({b.wojewodztwo})")
        for b in Beneficjent.query.filter_by(user_id=zajecia.user_id).all()
    ]
    if request.method == "GET":
        if zajecia.beneficjenci:
            form.beneficjenci.data = zajecia.beneficjenci[0].id
    try:
        if form.validate_on_submit():
            zajecia.data = form.data.data
            zajecia.godzina_od = form.godzina_od.data
            zajecia.godzina_do = form.godzina_do.data
            beneficjent = db.session.get(Beneficjent, form.beneficjenci.data)
            zajecia.beneficjenci = [beneficjent]
            db.session.commit()
            flash("Zajęcia zaktualizowane.")
            return redirect(url_for("admin.admin_zajecia"))
    except ValidationError:
        pass
    return render_template("zajecia_form.html", form=form)


@admin_bp.route("/zajecia/<int:zajecia_id>/usun", methods=["POST"])
@login_required
@admin_required
def admin_usun_zajecia(zajecia_id):
    """Admin action to remove a session."""
    form = DeleteForm()
    if form.validate_on_submit():
        zajecia = Zajecia.query.get_or_404(zajecia_id)
        db.session.delete(zajecia)
        db.session.commit()
        flash("Zajęcia usunięte.")
    return redirect(url_for("admin.admin_zajecia"))


@admin_bp.route("/instruktorzy")
@login_required
@admin_required
def admin_instruktorzy():
    """List all instructor accounts."""
    instructors = User.query.filter_by(role=Roles.INSTRUCTOR).all()
    delete_form = DeleteForm()
    promote_form = PromoteForm()
    confirm_form = ConfirmForm()
    return render_template(
        "admin/instructors_list.html",
        instructors=instructors,
        delete_form=delete_form,
        promote_form=promote_form,
        confirm_form=confirm_form,
    )


@admin_bp.route("/instruktorzy/<int:user_id>/edytuj", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edytuj_instruktora(user_id):
    """Admin view for editing an instructor account."""
    instr = User.query.get_or_404(user_id)
    form = UserEditForm(obj=instr)
    if form.validate_on_submit():
        instr.full_name = form.full_name.data
        instr.email = form.email.data
        db.session.commit()
        flash("Instruktor zaktualizowany.")
        return redirect(url_for("admin.admin_instruktorzy"))
    return render_template(
        "instructor_form.html", form=form, title="Edytuj instruktora"
    )


@admin_bp.route("/instruktorzy/<int:user_id>/usun", methods=["POST"])
@login_required
@admin_required
def admin_usun_instruktora(user_id):
    """Admin action to delete an instructor."""
    form = DeleteForm()
    if form.validate_on_submit():
        instr = User.query.get_or_404(user_id)
        db.session.delete(instr)
        db.session.commit()
        flash("Instruktor usunięty.")
    return redirect(url_for("admin.admin_instruktorzy"))


@admin_bp.route("/instruktorzy/<int:user_id>/promote", methods=["POST"])
@login_required
@admin_required
def admin_promote_instruktora(user_id):
    """Grant admin role to the selected instructor."""
    form = PromoteForm()
    if form.validate_on_submit():
        instr = User.query.get_or_404(user_id)
        instr.role = Roles.ADMIN
        db.session.commit()
        flash("Instruktor ma teraz uprawnienia admina.")
    return redirect(url_for("admin.admin_instruktorzy"))


@admin_bp.route("/instruktorzy/<int:user_id>/confirm", methods=["GET", "POST"])
@login_required
@admin_required
def admin_confirm_instruktora(user_id):
    """Confirm an instructor account registration."""
    if request.method == "GET":
        token = request.args.get("token")
        user = User.verify_confirm_token(token)
        if user and user.id == user_id:
            user.confirmed = True
            db.session.commit()
            flash("Instruktor został potwierdzony.")
        else:
            flash("Nieprawidłowy token potwierdzenia.")
        return redirect(url_for("admin.admin_instruktorzy"))

    form = ConfirmForm()
    if form.validate_on_submit():
        instr = User.query.get_or_404(user_id)
        instr.confirmed = True
        db.session.commit()
        flash("Instruktor został potwierdzony.")
    return redirect(url_for("admin.admin_instruktorzy"))


@admin_bp.route("/ustawienia", methods=["GET", "POST"])
@login_required
@admin_required
def admin_ustawienia():
    """View and edit application settings."""
    settings = Settings.get()
    if not settings:
        settings = Settings(
            mail_port=25,
            mail_use_tls=False,
            mail_use_ssl=False,
            admin_email=os.environ.get("ADMIN_EMAIL"),
            mail_sender_name=None,
        )
        db.session.add(settings)
        db.session.commit()
        current_app.config["MAIL_SERVER"] = (
            settings.mail_server or current_app.config["MAIL_SERVER"]
        )
        if settings.mail_port is not None:
            current_app.config["MAIL_PORT"] = settings.mail_port
        current_app.config["MAIL_USERNAME"] = (
            settings.mail_username or current_app.config["MAIL_USERNAME"]
        )
        current_app.config["MAIL_PASSWORD"] = (
            settings.mail_password or current_app.config["MAIL_PASSWORD"]
        )
        current_app.config["MAIL_USE_TLS"] = settings.mail_use_tls
        current_app.config["MAIL_USE_SSL"] = settings.mail_use_ssl
        current_app.config["TIMEZONE"] = (
            settings.timezone or current_app.config["TIMEZONE"]
        )
        if settings.admin_email:
            current_app.config["MAIL_DEFAULT_SENDER"] = (
                settings.mail_sender_name or "",
                settings.admin_email,
            )
        mail.init_app(current_app)
    form = SettingsForm(obj=settings)
    if form.validate_on_submit():
        if form.send_test.data:
            admin_email = settings.admin_email or os.environ.get("ADMIN_EMAIL")
            if admin_email:
                _, status = send_email(
                    "Test email",
                    [admin_email],
                    "To jest test konfiguracji SMTP.",
                )
                if status == "sent":
                    flash("Testowy email wysłany.")
                else:
                    flash("Nie udało się wysłać testowego emaila.")
            else:
                flash("Adres administratora nie jest skonfigurowany.")
            return redirect(url_for("admin.admin_ustawienia"))
        settings.mail_server = form.mail_server.data
        settings.mail_port = form.mail_port.data
        settings.mail_username = form.mail_username.data
        settings.mail_password = form.mail_password.data
        settings.mail_use_tls = form.mail_use_tls.data
        settings.mail_use_ssl = form.mail_use_ssl.data
        settings.admin_email = form.admin_email.data
        settings.mail_sender_name = form.sender_name.data
        settings.timezone = form.timezone.data
        db.session.commit()
        current_app.config["MAIL_SERVER"] = settings.mail_server or current_app.config["MAIL_SERVER"]
        if settings.mail_port is not None:
            current_app.config["MAIL_PORT"] = settings.mail_port
        current_app.config["MAIL_USERNAME"] = settings.mail_username or current_app.config["MAIL_USERNAME"]
        current_app.config["MAIL_PASSWORD"] = settings.mail_password or current_app.config["MAIL_PASSWORD"]
        current_app.config["MAIL_USE_TLS"] = settings.mail_use_tls
        current_app.config["MAIL_USE_SSL"] = settings.mail_use_ssl
        if settings.admin_email:
            current_app.config["MAIL_DEFAULT_SENDER"] = (
                settings.mail_sender_name or "",
                settings.admin_email,
            )
        current_app.config["TIMEZONE"] = settings.timezone or current_app.config["TIMEZONE"]
        mail.init_app(current_app)
        flash("Ustawienia zapisane.")
        return redirect(url_for("admin.admin_ustawienia"))
    return render_template("admin/settings_form.html", form=form)

