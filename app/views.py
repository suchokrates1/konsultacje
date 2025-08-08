from flask import render_template, redirect, url_for
from app import app, db, mail
from app.forms import RegisterForm
from app.models import Zajecia, User
from app.utils import (
    flash_success,
    flash_error,
    get_object_or_404,
    validate_form,
)
from flask_mail import Message
from smtplib import SMTPException
from werkzeug.exceptions import HTTPException


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if validate_form(form):
        if User.query.filter_by(email=form.email.data).first():
            flash_error('Użytkownik z tym adresem email już istnieje.')
            return render_template('register.html', form=form)

        user = User(
            full_name=form.full_name.data,
            email=form.email.data,
            confirmed=False,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        try:
            token = user.get_confirm_token()
            confirm_url = url_for(
                'confirm_account', token=token, _external=True
            )
            msg = Message('Potwierdzenie rejestracji', recipients=[user.email])
            msg.body = (
                'Aby potwierdzić rejestrację, kliknij w poniższy link:\n'
                f'{confirm_url}'
            )
            mail.send(msg)
        except SMTPException:
            flash_error('Nie udało się wysłać maila potwierdzającego.')

        flash_success(
            'Konto zostało utworzone. Sprawdź email, aby potwierdzić '
            'rejestrację.'
        )
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/zajecia/<int:zajecia_id>')
def zajecia_detail(zajecia_id):
    try:
        zajecia = get_object_or_404(Zajecia, zajecia_id)
    except HTTPException:
        flash_error('Zajęcia nie zostały znalezione.')
        return redirect(url_for('index'))
    return render_template('zajecia_detail.html', zajecia=zajecia)
