"""Views related to session management and beneficiaries."""

import os
import re
from datetime import datetime, timedelta

import pytz
from email_validator import EmailNotValidError, validate_email
from flask import (
    Blueprint,
    abort,
    after_this_request,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from wtforms.validators import ValidationError

from .. import db
from ..forms import BeneficjentForm, DeleteForm, ZajeciaForm
from ..models import Beneficjent, SentEmail, User, Zajecia
from ..utils import send_session_docx


sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/")
def index():
    """Serve the dashboard for authenticated users or the login page otherwise."""
    if current_user.is_authenticated:
        return redirect(url_for("sessions.nowe_zajecia"))
    from ..auth.routes import login as auth_login

    return auth_login()


@sessions_bp.route("/dashboard")
@login_required
def dashboard():
    """Provide a dashboard view for tests, showing the session list."""
    return lista_zajec()


@sessions_bp.route("/zajecia/nowe", methods=["GET", "POST"])
@login_required
def nowe_zajecia():
    """Create a new consultation session."""
    form = ZajeciaForm()
    messages = []
    form.beneficjenci.choices = [
        (b.id, f"{b.imie} ({b.wojewodztwo})")
        for b in Beneficjent.query.filter_by(user_id=current_user.id)
        .order_by(Beneficjent.imie)
        .all()
    ]

    if request.method == "GET":
        tz = pytz.timezone(current_app.config["TIMEZONE"])
        now = datetime.now(tz)
        rounded = (now + timedelta(minutes=30 - now.minute % 30)).replace(
            second=0, microsecond=0
        )
        form.data.data = now.date()
        form.godzina_od.data = rounded.time()
        form.godzina_do.data = (
            rounded + timedelta(minutes=current_user.default_duration)
        ).time()
        form.specjalista.data = current_user.session_type

    if form.validate_on_submit():
        zajecia = Zajecia(
            data=form.data.data,
            godzina_od=form.godzina_od.data,
            godzina_do=form.godzina_do.data,
            specjalista=form.specjalista.data,
            user_id=current_user.id,
        )
        beneficjent = db.session.get(Beneficjent, form.beneficjenci.data)
        zajecia.beneficjenci = [beneficjent]

        db.session.add(zajecia)
        db.session.commit()

        if form.submit_send.data:
            recipient = request.form.get("recipient_email")
            if recipient:
                try:
                    validate_email(recipient, check_deliverability=False)
                except EmailNotValidError:
                    flash("Niepoprawny adres email odbiorcy dokumentów.")
                    messages.append("Zajęcia zapisane.")
                    flash(" ".join(messages))
                    return redirect(url_for("sessions.lista_zajec"))
                if recipient != current_user.document_recipient_email:
                    current_user.document_recipient_email = recipient
                    db.session.commit()
            else:
                recipient = current_user.document_recipient_email
            if recipient:
                sent_at, status = send_session_docx(
                    zajecia, recipient, "Dokument z konsultacji"
                )
                if status == "sent":
                    zajecia.doc_sent_at = sent_at
                    messages.append("Dokument wysłany.")
                else:
                    flash("Nie udało się wysłać dokumentu.")

                sent_email = SentEmail(
                    zajecia_id=zajecia.id,
                    recipient=recipient,
                    subject="Dokument z konsultacji",
                    sent_at=sent_at,
                    status=status,
                )
                db.session.add(sent_email)
                db.session.commit()
            else:
                flash("Nie podano adresu email odbiorcy dokumentów.")

        messages.append("Zajęcia zapisane.")
        flash(" ".join(messages))
        return redirect(url_for("sessions.lista_zajec"))

    return render_template("zajecia_form.html", form=form)


@sessions_bp.route("/zajecia/<int:zajecia_id>/docx")
@login_required
def pobierz_docx(zajecia_id):
    """Generate and return a DOCX report for the given session."""
    zajecia = Zajecia.query.get_or_404(zajecia_id)
    if zajecia.user_id != current_user.id:
        flash("Brak dostępu do tych zajęć.")
        return redirect(url_for("sessions.index"))

    beneficjenci = zajecia.beneficjenci
    output_dir = os.path.join(current_app.root_path, "static", "docx")
    os.makedirs(output_dir, exist_ok=True)

    first_name = beneficjenci[0].imie if beneficjenci else "beneficjent"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", first_name)
    date_str = zajecia.data.strftime("%Y-%m-%d")
    filename = f"Konsultacje z {zajecia.specjalista} {date_str} {safe_name}.docx"
    output_path = os.path.join(output_dir, filename)

    from .. import routes

    routes.generate_docx(zajecia, beneficjenci, output_path)

    @after_this_request
    def remove_file(response):
        try:
            os.remove(output_path)
        except OSError:
            current_app.logger.warning("Failed to remove generated DOCX %s", output_path)
        return response

    return send_file(output_path, as_attachment=True, download_name=filename)


@sessions_bp.route("/zajecia/<int:zajecia_id>/send")
@login_required
def wyslij_docx(zajecia_id):
    """Regenerate a DOCX report and email it to the configured recipient."""
    zajecia = Zajecia.query.get_or_404(zajecia_id)
    if zajecia.user_id != current_user.id:
        flash("Brak dostępu do tych zajęć.")
        return redirect(url_for("sessions.lista_zajec"))

    recipient = zajecia.user.document_recipient_email
    if not recipient:
        flash("Brak ustawionego adresu odbiorcy dokumentu.")
        return redirect(url_for("sessions.lista_zajec"))

    sent_at, status = send_session_docx(zajecia, recipient, "Raport zajęć")
    if status == "sent":
        zajecia.doc_sent_at = sent_at
        flash("Raport wysłany ponownie.")
    else:
        flash("Nie udało się wysłać raportu.")

    sent_email = SentEmail(
        zajecia_id=zajecia.id,
        recipient=recipient,
        subject="Raport zajęć",
        sent_at=sent_at,
        status=status,
    )
    db.session.add(sent_email)
    db.session.commit()

    return redirect(url_for("sessions.lista_zajec"))


@sessions_bp.route("/emails")
@login_required
def emails_list():
    """List sent emails for the current user."""
    emails = (
        SentEmail.query.join(Zajecia)
        .filter(Zajecia.user_id == current_user.id)
        .order_by(SentEmail.sent_at.desc())
        .all()
    )
    return render_template("emails_list.html", emails=emails)


@sessions_bp.route("/emails/<int:email_id>/resend")
@login_required
def resend_email(email_id):
    """Regenerate attachment and resend the email."""
    sent_email = SentEmail.query.get_or_404(email_id)
    if not sent_email.zajecia or sent_email.zajecia.user_id != current_user.id:
        flash("Brak dostępu do tej wiadomości.")
        return redirect(url_for("sessions.emails_list"))

    zajecia = sent_email.zajecia
    recipient = sent_email.recipient
    subject = sent_email.subject

    sent_at, status = send_session_docx(zajecia, recipient, subject)
    if status == "sent":
        zajecia.doc_sent_at = sent_at
        flash("Wiadomość wysłana ponownie.")
    else:
        flash("Nie udało się wysłać raportu ponownie.")

    sent_email.sent_at = sent_at
    sent_email.status = status
    db.session.commit()
    return redirect(url_for("sessions.emails_list"))


@sessions_bp.route("/zajecia")
@login_required
def lista_zajec():
    """List sessions belonging to the current user with optional search."""
    q = request.args.get("q", "").strip()
    query = Zajecia.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(
            db.cast(Zajecia.data, db.String).ilike(f"%{q}%")
            | Zajecia.specjalista.ilike(f"%{q}%")
        )
    zajecia_list = (
        query.order_by(Zajecia.data.desc(), Zajecia.godzina_od.desc()).all()
    )
    delete_form = DeleteForm()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "_zajecia_rows.html", zajecia_list=zajecia_list, delete_form=delete_form
        )
    return render_template(
        "zajecia_list.html", zajecia_list=zajecia_list, q=q, delete_form=delete_form
    )


@sessions_bp.route("/zajecia/<int:zajecia_id>/edytuj", methods=["GET", "POST"])
@login_required
def edytuj_zajecia(zajecia_id):
    """Edit an existing session belonging to the current user."""
    zajecia = Zajecia.query.get_or_404(zajecia_id)
    if zajecia.user_id != current_user.id:
        flash("Brak dostępu do tych zajęć.")
        return redirect(url_for("sessions.lista_zajec"))

    form = ZajeciaForm(obj=zajecia)
    form.beneficjenci.choices = [
        (b.id, f"{b.imie} ({b.wojewodztwo})")
        for b in Beneficjent.query.filter_by(user_id=current_user.id).all()
    ]
    if request.method == "GET":
        if zajecia.beneficjenci:
            form.beneficjenci.data = zajecia.beneficjenci[0].id
        form.specjalista.data = current_user.session_type

    if form.validate_on_submit():
        zajecia.data = form.data.data
        zajecia.godzina_od = form.godzina_od.data
        zajecia.godzina_do = form.godzina_do.data
        zajecia.specjalista = form.specjalista.data
        beneficjent = db.session.get(Beneficjent, form.beneficjenci.data)
        zajecia.beneficjenci = [beneficjent]
        db.session.commit()
        flash("Zajęcia zaktualizowane.")
        return redirect(url_for("sessions.lista_zajec"))

    return render_template("zajecia_form.html", form=form)


@sessions_bp.route("/zajecia/<int:zajecia_id>/usun", methods=["POST"])
@login_required
def usun_zajecia(zajecia_id):
    """Delete a session owned by the current user."""
    form = DeleteForm()
    if form.validate_on_submit():
        zajecia = Zajecia.query.get_or_404(zajecia_id)
        if zajecia.user_id != current_user.id:
            flash("Brak dostępu do tych zajęć.")
            return redirect(url_for("sessions.lista_zajec"))
        db.session.delete(zajecia)
        db.session.commit()
        flash("Zajęcia usunięte.")
    return redirect(url_for("sessions.lista_zajec"))


@sessions_bp.route("/kalendarz")
@login_required
def kalendarz():
    """Display a calendar with upcoming sessions for the user."""
    tz = pytz.timezone(current_app.config["TIMEZONE"])
    today = datetime.now(tz).date()
    zajecia_list = (
        Zajecia.query.filter_by(user_id=current_user.id)
        .filter(Zajecia.data >= today)
        .order_by(Zajecia.data, Zajecia.godzina_od)
        .all()
    )
    return render_template("zajecia_calendar.html", zajecia_list=zajecia_list)


@sessions_bp.route("/api/zajecia")
@login_required
def api_zajecia():
    """Return upcoming sessions for the current user in JSON format."""
    tz = pytz.timezone(current_app.config["TIMEZONE"])
    today = datetime.now(tz).date()
    sessions = (
        Zajecia.query.filter_by(user_id=current_user.id)
        .filter(Zajecia.data >= today)
        .order_by(Zajecia.data, Zajecia.godzina_od)
        .all()
    )
    events = []
    for s in sessions:
        start_dt = tz.localize(datetime.combine(s.data, s.godzina_od))
        end_dt = tz.localize(datetime.combine(s.data, s.godzina_do))
        events.append(
            {
                "title": s.specjalista,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
            }
        )
    return jsonify(events)


@sessions_bp.route("/beneficjenci")
@login_required
def lista_beneficjentow():
    """List beneficiaries for the current user with optional search."""
    q = request.args.get("q", "").strip()
    query = Beneficjent.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(
            Beneficjent.imie.ilike(f"%{q}%")
            | Beneficjent.wojewodztwo.ilike(f"%{q}%")
        )
    beneficjenci = query.all()
    delete_form = DeleteForm()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render_template(
            "_beneficjenci_rows.html", beneficjenci=beneficjenci, delete_form=delete_form
        )
    return render_template(
        "beneficjenci_list.html",
        beneficjenci=beneficjenci,
        delete_form=delete_form,
        q=q,
    )


@sessions_bp.route("/beneficjenci/nowy", methods=["GET", "POST"])
@login_required
def nowy_beneficjent():
    """Create a new beneficiary entry."""
    form = BeneficjentForm()
    if form.validate_on_submit():
        beneficjent = Beneficjent(
            imie=form.imie.data,
            wojewodztwo=form.wojewodztwo.data,
            user_id=current_user.id,
        )
        db.session.add(beneficjent)
        db.session.commit()
        flash("Beneficjent dodany.")
        return redirect(url_for("sessions.lista_beneficjentow"))
    return render_template(
        "beneficjent_form.html", form=form, title="Nowy beneficjent"
    )


@sessions_bp.route(
    "/beneficjenci/<int:beneficjent_id>/edytuj", methods=["GET", "POST"]
)
@login_required
def edytuj_beneficjenta(beneficjent_id):
    """Edit an existing beneficiary belonging to the user."""
    benef = Beneficjent.query.get_or_404(beneficjent_id)
    if benef.user_id != current_user.id:
        flash("Brak dostępu do tego beneficjenta.")
        return redirect(url_for("sessions.lista_beneficjentow"))
    form = BeneficjentForm(obj=benef)
    if form.validate_on_submit():
        benef.imie = form.imie.data
        benef.wojewodztwo = form.wojewodztwo.data
        db.session.commit()
        flash("Beneficjent zaktualizowany.")
        return redirect(url_for("sessions.lista_beneficjentow"))
    return render_template(
        "beneficjent_form.html", form=form, title="Edytuj beneficjenta"
    )


@sessions_bp.route("/beneficjenci/<int:beneficjent_id>/usun", methods=["POST"])
@login_required
def usun_beneficjenta(beneficjent_id):
    """Delete a beneficiary owned by the current user."""
    form = DeleteForm()
    if form.validate_on_submit():
        benef = Beneficjent.query.get_or_404(beneficjent_id)
        if benef.user_id != current_user.id:
            flash("Brak dostępu do tego beneficjenta.")
            return redirect(url_for("sessions.lista_beneficjentow"))
        db.session.delete(benef)
        db.session.commit()
        flash("Beneficjent usunięty.")
    return redirect(url_for("sessions.lista_beneficjentow"))

