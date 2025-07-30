"""Flask view functions and the login form."""

import os
from datetime import datetime, timedelta

from flask import (
    current_app as app,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from flask_mail import Message

from . import db
from .forms import (
    ZajeciaForm,
    RegisterForm,
    PasswordResetRequestForm,
    PasswordResetForm,
    BeneficjentForm,
    DeleteForm,
)
from .models import Beneficjent, User, Zajecia
from . import mail
from .pdf_generator import generate_pdf
from urllib.parse import urlparse


class LoginForm(FlaskForm):
    """Form used by users to authenticate to the application."""
    username = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj się')


@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            if not next_url or urlparse(next_url).netloc != "":
                next_url = url_for('dashboard')
            return redirect(next_url)
        flash('Nieprawidłowe dane logowania.')
    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        admin_email = os.environ.get('ADMIN_EMAIL')
        if admin_email:
            msg = Message('New user registration', recipients=[admin_email])
            msg.body = (
                f'Użytkownik {user.username} zarejestrował się z adresem {user.email}.'
            )
            mail.send(msg)

        flash('Rejestracja zakończona sukcesem.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username)


@app.route('/zajecia/nowe', methods=['GET', 'POST'])
@login_required
def nowe_zajecia():
    form = ZajeciaForm()
    form.beneficjenci.choices = [
        (b.id, f"{b.imie} ({b.wojewodztwo})")
        for b in Beneficjent.query.filter_by(user_id=current_user.id).all()
    ]

    # Ustawienie domyślnych godzin po zaokrągleniu
    if request.method == 'GET':
        now = datetime.now()
        rounded = (
            now + timedelta(minutes=30 - now.minute % 30)
        ).replace(second=0, microsecond=0)
        form.data.data = now.date()
        form.godzina_od.data = rounded.time()
        form.godzina_do.data = (
            rounded + timedelta(minutes=current_user.default_duration)
        ).time()

    if form.validate_on_submit():
        zajecia = Zajecia(
            data=form.data.data,
            godzina_od=form.godzina_od.data,
            godzina_do=form.godzina_do.data,
            specjalista=current_user.username,
            user_id=current_user.id
        )
        for b_id in form.beneficjenci.data:
            beneficjent = Beneficjent.query.get(b_id)
            zajecia.beneficjenci.append(beneficjent)

        db.session.add(zajecia)
        db.session.commit()
        flash('Zajęcia zapisane.')
        return redirect(url_for('dashboard'))

    return render_template('zajecia_form.html', form=form)


@app.route('/zajecia/<int:zajecia_id>/pdf')
@login_required
def pobierz_pdf(zajecia_id):
    zajecia = Zajecia.query.get_or_404(zajecia_id)
    if zajecia.user_id != current_user.id:
        flash("Brak dostępu do tych zajęć.")
        return redirect(url_for('dashboard'))

    beneficjenci = zajecia.beneficjenci
    output_dir = os.path.join(current_app.root_path, "static", "pdf")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"zajecia_{zajecia.id}.pdf")

    generate_pdf(zajecia, beneficjenci, output_path)

    return send_file(output_path, as_attachment=True)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for('reset_password', token=token, _external=True)
            msg = Message('Reset hasła', recipients=[user.email])
            msg.body = f'Kliknij link aby zresetować hasło: {reset_url}'
            mail.send(msg)
        flash('Jeśli podany email istnieje, wysłano instrukcje resetowania hasła.')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
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


@app.route('/zajecia')
@login_required
def lista_zajec():
    zajecia_list = (
        Zajecia.query.filter_by(user_id=current_user.id)
        .order_by(Zajecia.data.desc(), Zajecia.godzina_od.desc())
        .all()
    )
    return render_template('zajecia_list.html', zajecia_list=zajecia_list)


@app.route('/beneficjenci')
@login_required
def lista_beneficjentow():
    beneficjenci = Beneficjent.query.filter_by(user_id=current_user.id).all()
    delete_form = DeleteForm()
    return render_template(
        'beneficjenci_list.html',
        beneficjenci=beneficjenci,
        delete_form=delete_form,
    )


@app.route('/beneficjenci/nowy', methods=['GET', 'POST'])
@login_required
def nowy_beneficjent():
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


@app.route('/beneficjenci/<int:beneficjent_id>/edytuj', methods=['GET', 'POST'])
@login_required
def edytuj_beneficjenta(beneficjent_id):
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
