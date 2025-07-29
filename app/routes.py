from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import User
from flask import Blueprint
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
import os
from flask import send_file
from .pdf_generator import generate_pdf


from flask import current_app as app

class LoginForm(FlaskForm):
    username = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    submit = SubmitField('Zaloguj się')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Nieprawidłowe dane logowania.')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.username)
from datetime import datetime, timedelta
from .forms import ZajeciaForm
from .models import Beneficjent, Zajecia, zajecia_beneficjenci

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
        rounded = (now + timedelta(minutes=30 - now.minute % 30)).replace(second=0, microsecond=0)
        form.data.data = now.date()
        form.godzina_od.data = rounded.time()
        form.godzina_do.data = (rounded + timedelta(minutes=current_user.default_duration)).time()

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
    output_path = f"static/pdf/zajecia_{zajecia.id}.pdf"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    generate_pdf(zajecia, beneficjenci, output_path)

    return send_file(output_path, as_attachment=True)
