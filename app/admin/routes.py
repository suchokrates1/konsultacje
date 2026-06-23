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
    ActivateProjektForm,
    BeneficjentForm,
    ConfirmForm,
    DeleteForm,
    DemoteForm,
    PromoteForm,
    ProjektForm,
    SettingsForm,
    UserEditForm,
    ZajeciaForm,
)
from ..models import Beneficjent, Projekt, ProjectStatus, Roles, Settings, User, Zajecia
from ..projekt_utils import get_aktywny_projekt, resolve_admin_projekt, ustaw_jako_aktywny


admin_bp = Blueprint("admin", __name__)


def admin_required(view_func):
    """Decorate ``view_func`` to allow access for admin or superadmin users."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if (
            not current_user.is_authenticated
            or current_user.role not in {Roles.ADMIN, Roles.SUPERADMIN}
        ):
            return abort(403)
        return view_func(*args, **kwargs)

    return wrapper


def superadmin_required(view_func):
    """Decorate ``view_func`` to allow access only for superadmin users."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != Roles.SUPERADMIN:
            return abort(403)
        return view_func(*args, **kwargs)

    return wrapper


@admin_bp.route("/beneficjenci")
@login_required
@admin_required
def admin_beneficjenci():
    """Show beneficiaries for the selected project."""
    selected_projekt = resolve_admin_projekt()
    projekty = Projekt.query.order_by(Projekt.utworzono.desc()).all()
    query = Beneficjent.query
    if selected_projekt:
        query = query.filter_by(project_id=selected_projekt.id)
    beneficjenci = query.all()
    delete_form = DeleteForm()
    return render_template(
        "admin/beneficjenci_list.html",
        beneficjenci=beneficjenci,
        delete_form=delete_form,
        projekty=projekty,
        selected_projekt=selected_projekt,
    )


@admin_bp.route("/beneficjenci/<int:beneficjent_id>/edytuj", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edytuj_beneficjenta(beneficjent_id):
    """Admin view for editing any beneficiary."""
    benef = db.session.get(Beneficjent, beneficjent_id)
    if benef is None:
        current_app.logger.warning(
            "admin_edytuj_beneficjenta: beneficjent %s not found", beneficjent_id
        )
        abort(404)
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
        benef = db.session.get(Beneficjent, beneficjent_id)
        if benef is None:
            current_app.logger.warning(
                "admin_usun_beneficjenta: beneficjent %s not found", beneficjent_id
            )
            abort(404)
        db.session.delete(benef)
        db.session.commit()
        flash("Beneficjent usunięty.")
    return redirect(url_for("admin.admin_beneficjenci"))


@admin_bp.route("/zajecia")
@login_required
@admin_required
def admin_zajecia():
    """Display sessions for the selected project."""
    selected_projekt = resolve_admin_projekt()
    projekty = Projekt.query.order_by(Projekt.utworzono.desc()).all()
    query = Zajecia.query
    if selected_projekt:
        query = query.filter_by(project_id=selected_projekt.id)
    zajecia_list = query.order_by(
        Zajecia.data.desc(), Zajecia.godzina_od.desc()
    ).all()
    delete_form = DeleteForm()
    return render_template(
        "admin/zajecia_list.html",
        zajecia_list=zajecia_list,
        delete_form=delete_form,
        projekty=projekty,
        selected_projekt=selected_projekt,
    )


@admin_bp.route("/zajecia/<int:zajecia_id>/edytuj", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edytuj_zajecia(zajecia_id):
    """Admin view for editing any session."""
    zajecia = db.session.get(Zajecia, zajecia_id)
    if zajecia is None:
        current_app.logger.warning(
            "admin_edytuj_zajecia: zajecia %s not found", zajecia_id
        )
        abort(404)
    form = ZajeciaForm(obj=zajecia)
    form.beneficjenci.choices = [
        (b.id, f"{b.imie} ({b.wojewodztwo})")
        for b in Beneficjent.query.filter_by(
            user_id=zajecia.user_id, project_id=zajecia.project_id
        ).all()
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
            return redirect(
                url_for(
                    "admin.admin_zajecia",
                    projekt_id=zajecia.project_id,
                )
            )
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
        zajecia = db.session.get(Zajecia, zajecia_id)
        if zajecia is None:
            current_app.logger.warning(
                "admin_usun_zajecia: zajecia %s not found", zajecia_id
            )
            abort(404)
        db.session.delete(zajecia)
        db.session.commit()
        flash("Zajęcia usunięte.")
    projekt_id = request.form.get("projekt_id", type=int)
    if projekt_id:
        return redirect(url_for("admin.admin_zajecia", projekt_id=projekt_id))
    return redirect(url_for("admin.admin_zajecia"))


@admin_bp.route("/uzytkownicy")
@login_required
@admin_required
def admin_uzytkownicy():
    """List all instructor and admin accounts."""
    instructors = User.query.filter_by(role=Roles.INSTRUCTOR).all()
    admins = User.query.filter_by(role=Roles.ADMIN).all()
    delete_form = DeleteForm()
    promote_form = PromoteForm()
    demote_form = DemoteForm()
    confirm_form = ConfirmForm()
    return render_template(
        "admin/users_list.html",
        instructors=instructors,
        admins=admins,
        delete_form=delete_form,
        promote_form=promote_form,
        demote_form=demote_form,
        confirm_form=confirm_form,
        Roles=Roles,
    )


@admin_bp.route("/uzytkownicy/<int:user_id>/edytuj", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edytuj_uzytkownika(user_id):
    """Admin view for editing a user account."""
    instr = db.session.get(User, user_id)
    if instr is None:
        current_app.logger.warning(
            "admin_edytuj_uzytkownika: user %s not found", user_id
        )
        abort(404)
    if instr.role == Roles.ADMIN and current_user.role != Roles.SUPERADMIN:
        abort(403)
    form = UserEditForm(obj=instr)
    if form.validate_on_submit():
        instr.full_name = form.full_name.data
        instr.email = form.email.data
        db.session.commit()
        flash("Użytkownik zaktualizowany.")
        return redirect(url_for("admin.admin_uzytkownicy"))
    return render_template(
        "instructor_form.html", form=form, title="Edytuj użytkownika"
    )


@admin_bp.route("/uzytkownicy/<int:user_id>/usun", methods=["POST"])
@login_required
@admin_required
def admin_usun_uzytkownika(user_id):
    """Admin action to delete a user."""
    form = DeleteForm()
    if form.validate_on_submit():
        instr = db.session.get(User, user_id)
        if instr is None:
            current_app.logger.warning(
                "admin_usun_uzytkownika: user %s not found", user_id
            )
            abort(404)
        if instr.role == Roles.ADMIN and current_user.role != Roles.SUPERADMIN:
            abort(403)
        db.session.delete(instr)
        db.session.commit()
        flash("Użytkownik usunięty.")
    return redirect(url_for("admin.admin_uzytkownicy"))


@admin_bp.route("/uzytkownicy/<int:user_id>/promote", methods=["POST"])
@login_required
@admin_required
def admin_promote_uzytkownika(user_id):
    """Grant admin role to the selected user."""
    form = PromoteForm()
    if form.validate_on_submit():
        instr = db.session.get(User, user_id)
        if instr is None:
            current_app.logger.warning(
                "admin_promote_uzytkownika: user %s not found", user_id
            )
            abort(404)
        instr.role = Roles.ADMIN
        db.session.commit()
        flash("Użytkownik ma teraz uprawnienia admina.")
    return redirect(url_for("admin.admin_uzytkownicy"))


@admin_bp.route("/uzytkownicy/<int:user_id>/demote", methods=["POST"])
@login_required
@superadmin_required
def admin_demote_admin(user_id):
    """Demote an admin user back to instructor."""
    form = DemoteForm()
    if form.validate_on_submit():
        user = db.session.get(User, user_id)
        if user is None:
            current_app.logger.warning(
                "admin_demote_admin: user %s not found", user_id
            )
            abort(404)
        if user.role != Roles.ADMIN:
            current_app.logger.warning(
                "admin_demote_admin: user %s is not admin", user_id
            )
            abort(403)
        user.role = Roles.INSTRUCTOR
        db.session.commit()
        flash("Użytkownik został zdegradowany.")
    return redirect(url_for("admin.admin_uzytkownicy"))


@admin_bp.route("/uzytkownicy/<int:user_id>/confirm", methods=["GET", "POST"])
@login_required
@admin_required
def admin_confirm_uzytkownika(user_id):
    """Confirm a user account registration."""
    if request.method == "GET":
        token = request.args.get("token")
        user = User.verify_confirm_token(token)
        if user and user.id == user_id:
            user.confirmed = True
            db.session.commit()
            flash("Użytkownik został potwierdzony.")
        else:
            flash("Nieprawidłowy token potwierdzenia.")
        return redirect(url_for("admin.admin_uzytkownicy"))

    form = ConfirmForm()
    if form.validate_on_submit():
        instr = db.session.get(User, user_id)
        if instr is None:
            current_app.logger.warning(
                "admin_confirm_uzytkownika: user %s not found", user_id
            )
            abort(404)
        instr.confirmed = True
        db.session.commit()
        flash("Użytkownik został potwierdzony.")
    return redirect(url_for("admin.admin_uzytkownicy"))


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


@admin_bp.route("/projekty")
@login_required
@admin_required
def admin_projekty():
    """List all projects and allow activation of a new edition."""
    projekty = Projekt.query.order_by(Projekt.utworzono.desc()).all()
    activate_form = ActivateProjektForm()
    return render_template(
        "admin/projekty_list.html",
        projekty=projekty,
        activate_form=activate_form,
        ProjectStatus=ProjectStatus,
    )


@admin_bp.route("/projekty/nowy", methods=["GET", "POST"])
@login_required
@admin_required
def admin_nowy_projekt():
    """Create a new project (starts in archive)."""
    form = ProjektForm()
    if form.validate_on_submit():
        existing = Projekt.query.filter_by(nazwa=form.nazwa.data.strip()).first()
        if existing:
            flash("Projekt o tej nazwie już istnieje.")
        else:
            projekt = Projekt(
                nazwa=form.nazwa.data.strip(),
                status=ProjectStatus.ARCHIWUM,
            )
            db.session.add(projekt)
            db.session.commit()
            flash("Projekt utworzony.")
            return redirect(url_for("admin.admin_projekty"))
    return render_template(
        "admin/projekt_form.html", form=form, title="Nowy projekt"
    )


@admin_bp.route("/projekty/<int:projekt_id>/edytuj", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edytuj_projekt(projekt_id):
    """Edit project name."""
    projekt = db.session.get(Projekt, projekt_id)
    if projekt is None:
        abort(404)
    form = ProjektForm(obj=projekt)
    if form.validate_on_submit():
        nazwa = form.nazwa.data.strip()
        conflict = Projekt.query.filter(
            Projekt.nazwa == nazwa, Projekt.id != projekt.id
        ).first()
        if conflict:
            flash("Projekt o tej nazwie już istnieje.")
        else:
            projekt.nazwa = nazwa
            db.session.commit()
            flash("Projekt zaktualizowany.")
            return redirect(url_for("admin.admin_projekty"))
    return render_template(
        "admin/projekt_form.html", form=form, title="Edytuj projekt"
    )


@admin_bp.route("/projekty/<int:projekt_id>/aktywuj", methods=["POST"])
@login_required
@admin_required
def admin_aktywuj_projekt(projekt_id):
    """Set the given project as the active edition."""
    form = ActivateProjektForm()
    projekt = db.session.get(Projekt, projekt_id)
    if projekt is None:
        abort(404)
    if form.validate_on_submit():
        if projekt.status == ProjectStatus.AKTYWNY:
            flash("Ten projekt jest już obecny.")
        else:
            ustaw_jako_aktywny(projekt)
            flash(f"Projekt „{projekt.nazwa}” ustawiony jako obecny.")
    return redirect(url_for("admin.admin_projekty"))

