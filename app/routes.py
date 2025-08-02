"""Flask view functions and the login form."""

import os
import re
from datetime import datetime, timedelta
import pytz

from flask import (
    current_app as app,
    current_app,
    abort,
    flash,
    redirect,
    render_template,
    request,
    jsonify,
    send_file,
    url_for,
    after_this_request,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField, BooleanField, EmailField
from wtforms.validators import DataRequired, ValidationError, Email
from flask_mail import Message
from smtplib import SMTPException

from . import db
from .forms import (
    ZajeciaForm,
    RegisterForm,
    PasswordResetRequestForm,
    PasswordResetForm,
    UserSettingsForm,
    BeneficjentForm,
    DeleteForm,
    PromoteForm,
    ConfirmForm,
    UserEditForm,
    SettingsForm,
)
from .models import Beneficjent, User, Zajecia, Roles, Settings
from . import mail
from .docx_generator import generate_docx
from urllib.parse import urlparse
from functools import wraps


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


class LoginForm(FlaskForm):
    """Form used by users to authenticate to the application."""

    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj się')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate a user and redirect to the next page."""
    next_url = request.args.get('next')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.confirmed:
                flash('Twoje konto nie zostało jeszcze potwierdzone.')
                return render_template('login.html', form=form)
            login_user(user, remember=form.remember_me.data)
            if not next_url or urlparse(next_url).netloc != "":
                next_url = url_for('nowe_zajecia')
            return redirect(next_url)
        flash('Nieprawidłowe dane logowania.')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Create a new user account."""
    form = RegisterForm()
    if form.validate_on_submit():
        # prevent duplicate accounts with the same email address
        if User.query.filter_by(email=form.email.data).first():
            flash('Użytkownik z tym adresem email już istnieje.')
            return render_template('register.html', form=form)

        user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            confirmed=False,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        admin_cfg = current_app.config.get('MAIL_DEFAULT_SENDER')
        admin_email = os.environ.get('ADMIN_EMAIL')
        if isinstance(admin_cfg, tuple):
            admin_email = admin_cfg[1]
        elif admin_cfg:
            admin_email = admin_cfg
        if admin_email:
            msg = Message(
                'New user registration',
                recipients=[admin_email],
                sender=current_app.config['MAIL_DEFAULT_SENDER'],
            )
            msg.body = (
                f'Użytkownik {user.full_name} zarejestrował się z adresem '
                f'{user.email}. '
            )
            try:
                mail.send(msg)
            except SMTPException as e:
                current_app.logger.error(
                    "Failed to send admin email: %s", e
                )
                flash('Nie udało się wysłać powiadomienia do administratora.')

        flash('Rejestracja zakończona sukcesem. Poczekaj na potwierdzenie przez administratora.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Redirect authenticated users to the new session form."""
    return redirect(url_for('nowe_zajecia'))


@app.route('/zajecia/nowe', methods=['GET', 'POST'])
@login_required
def nowe_zajecia():
    """Create a new consultation session."""
    form = ZajeciaForm()
    form.beneficjenci.choices = [
        (b.id, f"{b.imie} ({b.wojewodztwo})")
        for b in Beneficjent.query.filter_by(user_id=current_user.id)
        .order_by(Beneficjent.imie)
        .all()
    ]

    # Ustawienie domyślnych godzin po zaokrągleniu
    if request.method == 'GET':
        tz = pytz.timezone(current_app.config['TIMEZONE'])
        now = datetime.now(tz)
        rounded = (
            now + timedelta(minutes=30 - now.minute % 30)
        ).replace(second=0, microsecond=0)
        form.data.data = now.date()
        form.godzina_od.data = rounded.time()
        form.godzina_do.data = (
            rounded + timedelta(minutes=current_user.default_duration)
        ).time()

    try:
        if form.validate_on_submit():
            zajecia = Zajecia(
                data=form.data.data,
                godzina_od=form.godzina_od.data,
                godzina_do=form.godzina_do.data,
                specjalista=current_user.full_name,
                user_id=current_user.id,
            )
            beneficjent = db.session.get(Beneficjent, form.beneficjenci.data)
            zajecia.beneficjenci = [beneficjent]

            db.session.add(zajecia)
            db.session.commit()
            flash('Zajęcia zapisane.')
            return redirect(url_for('lista_zajec'))
    except ValidationError:
        pass

    return render_template('zajecia_form.html', form=form)


@app.route('/zajecia/<int:zajecia_id>/docx')
@login_required
def pobierz_docx(zajecia_id):
    """Generate and return a DOCX report for the given session."""
    zajecia = Zajecia.query.get_or_404(zajecia_id)
    if zajecia.user_id != current_user.id:
        flash("Brak dostępu do tych zajęć.")
        return redirect(url_for('index'))

    beneficjenci = zajecia.beneficjenci
    output_dir = os.path.join(current_app.root_path, "static", "docx")
    os.makedirs(output_dir, exist_ok=True)

    first_name = beneficjenci[0].imie if beneficjenci else "beneficjent"
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", first_name)
    date_str = zajecia.data.strftime("%Y-%m-%d")
    filename = f"Konsultacje dietetyczne {date_str} {safe_name}.docx"
    output_path = os.path.join(output_dir, filename)

    generate_docx(zajecia, beneficjenci, output_path)

    @after_this_request
    def remove_file(response):
        try:
            os.remove(output_path)
        except OSError:
            current_app.logger.warning(
                "Failed to remove generated DOCX %s",
                output_path,
            )
        return response

    return send_file(output_path, as_attachment=True, download_name=filename)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Send a password reset link to the provided email address."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for(
                'reset_password', token=token, _external=True
            )
            msg = Message(
                'Reset hasła',
                recipients=[user.email],
                sender=current_app.config['MAIL_DEFAULT_SENDER'],
            )
            msg.body = (
                f'Kliknij link aby zresetować hasło: {reset_url}'
            )
            try:
                mail.send(msg)
            except SMTPException as e:
                current_app.logger.error(
                    "Failed to send password reset email: %s", e
                )
                flash('Nie udało się wysłać emaila z linkiem resetującym.')
        flash(
            'Jeśli podany email istnieje, wysłano instrukcje '
            'resetowania hasła.'
        )
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Allow the user to set a new password using a token."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_token(token)
    if not user:
        flash('Link resetujący jest nieważny lub wygasł.')
        return redirect(url_for('reset_password_request'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Hasło zostało zresetowane.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    """Display and update user account settings."""
    form = UserSettingsForm()
    if form.validate_on_submit():
        current_user.email = form.email.data
        current_user.full_name = form.full_name.data
        current_user.default_duration = form.default_duration.data
        if form.new_password.data:
            if not current_user.check_password(form.old_password.data):
                flash('Nieprawidłowe aktualne hasło.')
                return render_template('settings.html', form=form)
            current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Ustawienia zapisane.')
        return redirect(url_for('user_settings'))
    elif request.method == 'GET':
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name
        form.default_duration.data = current_user.default_duration
    return render_template('settings.html', form=form)


@app.route('/zajecia')
@login_required
def lista_zajec():
    """List sessions belonging to the current user with optional search."""
    q = request.args.get('q', '').strip()
    query = Zajecia.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(
            db.cast(Zajecia.data, db.String).ilike(f"%{q}%")
            | Zajecia.specjalista.ilike(f"%{q}%")
        )
    zajecia_list = (
        query.order_by(Zajecia.data.desc(), Zajecia.godzina_od.desc()).all()
    )
    return render_template('zajecia_list.html', zajecia_list=zajecia_list, q=q)


@app.route('/kalendarz')
@login_required
def kalendarz():
    """Display a calendar with upcoming sessions for the user."""
    tz = pytz.timezone(current_app.config['TIMEZONE'])
    today = datetime.now(tz).date()
    zajecia_list = (
        Zajecia.query.filter_by(user_id=current_user.id)
        .filter(Zajecia.data >= today)
        .order_by(Zajecia.data, Zajecia.godzina_od)
        .all()
    )
    return render_template('zajecia_calendar.html', zajecia_list=zajecia_list)


@app.route('/api/zajecia')
@login_required
def api_zajecia():
    """Return upcoming sessions for the current user in JSON format."""
    tz = pytz.timezone(current_app.config['TIMEZONE'])
    today = datetime.now(tz).date()
    sessions = (
        Zajecia.query.filter_by(user_id=current_user.id)
        .filter(Zajecia.data >= today)
        .order_by(Zajecia.data, Zajecia.godzina_od)
        .all()
    )
    events = []
    for s in sessions:
        start_dt = datetime.combine(s.data, s.godzina_od)
        end_dt = datetime.combine(s.data, s.godzina_do)
        events.append(
            {
                'title': s.specjalista,
                'start': start_dt.isoformat(),
                'end': end_dt.isoformat(),
            }
        )
    return jsonify(events)


@app.route('/beneficjenci')
@login_required
def lista_beneficjentow():
    """List beneficiaries for the current user with optional search."""
    q = request.args.get('q', '').strip()
    query = Beneficjent.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(
            Beneficjent.imie.ilike(f"%{q}%")
            | Beneficjent.wojewodztwo.ilike(f"%{q}%")
        )
    beneficjenci = query.all()
    delete_form = DeleteForm()
    return render_template(
        'beneficjenci_list.html',
        beneficjenci=beneficjenci,
        delete_form=delete_form,
        q=q,
    )


@app.route('/beneficjenci/nowy', methods=['GET', 'POST'])
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
        flash('Beneficjent dodany.')
        return redirect(url_for('lista_beneficjentow'))
    return render_template(
        'beneficjent_form.html', form=form, title='Nowy beneficjent'
    )


@app.route(
    '/beneficjenci/<int:beneficjent_id>/edytuj', methods=['GET', 'POST']
)
@login_required
def edytuj_beneficjenta(beneficjent_id):
    """Edit an existing beneficiary belonging to the user."""
    benef = Beneficjent.query.get_or_404(beneficjent_id)
    if benef.user_id != current_user.id:
        flash('Brak dostępu do tego beneficjenta.')
        return redirect(url_for('lista_beneficjentow'))
    form = BeneficjentForm(obj=benef)
    if form.validate_on_submit():
        benef.imie = form.imie.data
        benef.wojewodztwo = form.wojewodztwo.data
        db.session.commit()
        flash('Beneficjent zaktualizowany.')
        return redirect(url_for('lista_beneficjentow'))
    return render_template(
        'beneficjent_form.html', form=form, title='Edytuj beneficjenta'
    )


@app.route('/beneficjenci/<int:beneficjent_id>/usun', methods=['POST'])
@login_required
def usun_beneficjenta(beneficjent_id):
    """Delete a beneficiary owned by the current user."""
    form = DeleteForm()
    if form.validate_on_submit():
        benef = Beneficjent.query.get_or_404(beneficjent_id)
        if benef.user_id != current_user.id:
            flash('Brak dostępu do tego beneficjenta.')
            return redirect(url_for('lista_beneficjentow'))
        db.session.delete(benef)
        db.session.commit()
        flash('Beneficjent usunięty.')
    return redirect(url_for('lista_beneficjentow'))


# --------------------- Admin Views ---------------------


@app.route('/admin/beneficjenci')
@login_required
@admin_required
def admin_beneficjenci():
    """Show all beneficiaries to the admin user."""
    beneficjenci = Beneficjent.query.all()
    delete_form = DeleteForm()
    return render_template(
        'admin/beneficjenci_list.html',
        beneficjenci=beneficjenci,
        delete_form=delete_form,
    )


@app.route(
    '/admin/beneficjenci/<int:beneficjent_id>/edytuj', methods=['GET', 'POST']
)
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
        flash('Beneficjent zaktualizowany.')
        return redirect(url_for('admin_beneficjenci'))
    return render_template(
        'beneficjent_form.html', form=form, title='Edytuj beneficjenta'
    )


@app.route('/admin/beneficjenci/<int:beneficjent_id>/usun', methods=['POST'])
@login_required
@admin_required
def admin_usun_beneficjenta(beneficjent_id):
    """Admin action to delete a beneficiary."""
    form = DeleteForm()
    if form.validate_on_submit():
        benef = Beneficjent.query.get_or_404(beneficjent_id)
        db.session.delete(benef)
        db.session.commit()
        flash('Beneficjent usunięty.')
    return redirect(url_for('admin_beneficjenci'))


@app.route('/admin/zajecia')
@login_required
@admin_required
def admin_zajecia():
    """Display all sessions for the admin."""
    zajecia_list = Zajecia.query.order_by(
        Zajecia.data.desc(), Zajecia.godzina_od.desc()
    ).all()
    delete_form = DeleteForm()
    return render_template(
        'admin/zajecia_list.html',
        zajecia_list=zajecia_list,
        delete_form=delete_form,
    )


@app.route('/admin/zajecia/<int:zajecia_id>/edytuj', methods=['GET', 'POST'])
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
    if request.method == 'GET':
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
            flash('Zajęcia zaktualizowane.')
            return redirect(url_for('admin_zajecia'))
    except ValidationError:
        pass
    return render_template('zajecia_form.html', form=form)


@app.route('/admin/zajecia/<int:zajecia_id>/usun', methods=['POST'])
@login_required
@admin_required
def admin_usun_zajecia(zajecia_id):
    """Admin action to remove a session."""
    form = DeleteForm()
    if form.validate_on_submit():
        zajecia = Zajecia.query.get_or_404(zajecia_id)
        db.session.delete(zajecia)
        db.session.commit()
        flash('Zajęcia usunięte.')
    return redirect(url_for('admin_zajecia'))


@app.route('/admin/instruktorzy')
@login_required
@admin_required
def admin_instruktorzy():
    """List all instructor accounts."""
    instructors = User.query.filter_by(role=Roles.INSTRUCTOR).all()
    delete_form = DeleteForm()
    promote_form = PromoteForm()
    confirm_form = ConfirmForm()
    return render_template(
        'admin/instructors_list.html',
        instructors=instructors,
        delete_form=delete_form,
        promote_form=promote_form,
        confirm_form=confirm_form,
    )


@app.route('/admin/instruktorzy/<int:user_id>/edytuj', methods=['GET', 'POST'])
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
        flash('Instruktor zaktualizowany.')
        return redirect(url_for('admin_instruktorzy'))
    return render_template(
        'instructor_form.html', form=form, title='Edytuj instruktora'
    )


@app.route('/admin/instruktorzy/<int:user_id>/usun', methods=['POST'])
@login_required
@admin_required
def admin_usun_instruktora(user_id):
    """Admin action to delete an instructor."""
    form = DeleteForm()
    if form.validate_on_submit():
        instr = User.query.get_or_404(user_id)
        db.session.delete(instr)
        db.session.commit()
        flash('Instruktor usunięty.')
    return redirect(url_for('admin_instruktorzy'))


@app.route('/admin/instruktorzy/<int:user_id>/promote', methods=['POST'])
@login_required
@admin_required
def admin_promote_instruktora(user_id):
    """Grant admin role to the selected instructor."""
    form = PromoteForm()
    if form.validate_on_submit():
        instr = User.query.get_or_404(user_id)
        instr.role = Roles.ADMIN
        db.session.commit()
        flash('Instruktor ma teraz uprawnienia admina.')
    return redirect(url_for('admin_instruktorzy'))


@app.route('/admin/instruktorzy/<int:user_id>/confirm', methods=['POST'])
@login_required
@admin_required
def admin_confirm_instruktora(user_id):
    """Confirm an instructor account registration."""
    form = ConfirmForm()
    if form.validate_on_submit():
        instr = User.query.get_or_404(user_id)
        instr.confirmed = True
        db.session.commit()
        flash('Instruktor został potwierdzony.')
    return redirect(url_for('admin_instruktorzy'))


@app.route('/admin/ustawienia', methods=['GET', 'POST'])
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
            admin_email=os.environ.get('ADMIN_EMAIL'),
            mail_sender_name=None,
        )
        db.session.add(settings)
        db.session.commit()
        current_app.config['MAIL_SERVER'] = (
            settings.mail_server or current_app.config['MAIL_SERVER']
        )
        if settings.mail_port is not None:
            current_app.config['MAIL_PORT'] = settings.mail_port
        current_app.config['MAIL_USERNAME'] = (
            settings.mail_username or current_app.config['MAIL_USERNAME']
        )
        current_app.config['MAIL_PASSWORD'] = (
            settings.mail_password or current_app.config['MAIL_PASSWORD']
        )
        current_app.config['MAIL_USE_TLS'] = settings.mail_use_tls
        current_app.config['MAIL_USE_SSL'] = settings.mail_use_ssl
        current_app.config['TIMEZONE'] = (
            settings.timezone or current_app.config['TIMEZONE']
        )
        if settings.admin_email:
            current_app.config['MAIL_DEFAULT_SENDER'] = (
                settings.mail_sender_name or "",
                settings.admin_email,
            )
        mail.init_app(current_app)
    form = SettingsForm(obj=settings)
    if form.validate_on_submit():
        if form.send_test.data:
            admin_email = settings.admin_email or os.environ.get('ADMIN_EMAIL')
            if admin_email:
                msg = Message(
                    'Test email',
                    recipients=[admin_email],
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                )
                msg.body = 'To jest test konfiguracji SMTP.'
                try:
                    mail.send(msg)
                    flash('Testowy email wysłany.')
                except SMTPException as exc:
                    current_app.logger.error('Failed to send test email: %s', exc)
                    flash('Nie udało się wysłać testowego emaila.')
            else:
                flash('Adres administratora nie jest skonfigurowany.')
            return redirect(url_for('admin_ustawienia'))
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
        current_app.config['MAIL_SERVER'] = settings.mail_server or current_app.config['MAIL_SERVER']
        if settings.mail_port is not None:
            current_app.config['MAIL_PORT'] = settings.mail_port
        current_app.config['MAIL_USERNAME'] = settings.mail_username or current_app.config['MAIL_USERNAME']
        current_app.config['MAIL_PASSWORD'] = settings.mail_password or current_app.config['MAIL_PASSWORD']
        current_app.config['MAIL_USE_TLS'] = settings.mail_use_tls
        current_app.config['MAIL_USE_SSL'] = settings.mail_use_ssl
        if settings.admin_email:
            current_app.config['MAIL_DEFAULT_SENDER'] = (
                settings.mail_sender_name or "",
                settings.admin_email,
            )
        current_app.config['TIMEZONE'] = settings.timezone or current_app.config['TIMEZONE']
        mail.init_app(current_app)
        flash('Ustawienia zapisane.')
        return redirect(url_for('admin_ustawienia'))
    return render_template('admin/settings_form.html', form=form)


@app.errorhandler(404)
def not_found_error(error):
    """Render a custom 404 page."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Render a custom 500 page."""
    db.session.rollback()
    return render_template('500.html'), 500
