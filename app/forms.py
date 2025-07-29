from flask_wtf import FlaskForm
from wtforms import (
    SelectMultipleField,
    SubmitField,
    DateField,
    TimeField,
    StringField,
    PasswordField,
    EmailField,
)
from wtforms.validators import DataRequired, Email, EqualTo
from wtforms.widgets import ListWidget, CheckboxInput


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class ZajeciaForm(FlaskForm):
    data = DateField('Data konsultacji', validators=[DataRequired()])
    godzina_od = TimeField('Godzina od', validators=[DataRequired()])
    godzina_do = TimeField('Godzina do', validators=[DataRequired()])
    beneficjenci = MultiCheckboxField(
        'Beneficjenci', coerce=int, validators=[DataRequired()]
    )
    submit = SubmitField('Zapisz zajęcia')


class RegisterForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    confirm = PasswordField(
        'Potwierdź hasło',
        validators=[DataRequired(), EqualTo('password', message='Hasła muszą się zgadzać')],
    )
    submit = SubmitField('Zarejestruj się')


class PasswordResetRequestForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Wyślij link resetujący')


class PasswordResetForm(FlaskForm):
    password = PasswordField('Nowe hasło', validators=[DataRequired()])
    confirm = PasswordField(
        'Potwierdź hasło',
        validators=[DataRequired(), EqualTo('password', message='Hasła muszą się zgadzać')],
    )
    submit = SubmitField('Zresetuj hasło')


class BeneficjentForm(FlaskForm):
    imie = StringField('Imię i nazwisko', validators=[DataRequired()])
    wojewodztwo = StringField('Województwo', validators=[DataRequired()])
    submit = SubmitField('Zapisz')

