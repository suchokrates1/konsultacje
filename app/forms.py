"""WTForms used to validate and handle user input."""

from flask_wtf import FlaskForm
from wtforms import (
    SelectMultipleField,
    SubmitField,
    DateField,
    TimeField,
    StringField,
    PasswordField,
    EmailField,
    IntegerField,
)
from wtforms.validators import DataRequired, Email, EqualTo
from wtforms.widgets import ListWidget, CheckboxInput


class MultiCheckboxField(SelectMultipleField):
    """Multiple selection field rendered as a list of checkboxes."""

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class ZajeciaForm(FlaskForm):
    """Form for scheduling a consultation session."""

    data = DateField('Data konsultacji', validators=[DataRequired()])
    godzina_od = TimeField('Godzina od', validators=[DataRequired()])
    godzina_do = TimeField('Godzina do', validators=[DataRequired()])
    beneficjenci = SelectMultipleField(
        'Beneficjenci', coerce=int, validators=[DataRequired()]
    )
    submit = SubmitField('Zapisz zajęcia')


class RegisterForm(FlaskForm):
    """Form allowing new users to create an account."""

    full_name = StringField('Imię i nazwisko', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    confirm = PasswordField(
        'Potwierdź hasło',
        validators=[
            DataRequired(),
            EqualTo('password', message='Hasła muszą się zgadzać'),
        ],
    )
    submit = SubmitField('Zarejestruj się')


class PasswordResetRequestForm(FlaskForm):
    """Request form used to send a password reset link."""

    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Wyślij link resetujący')


class PasswordResetForm(FlaskForm):
    """Form for setting a new password after receiving a token."""

    password = PasswordField('Nowe hasło', validators=[DataRequired()])
    confirm = PasswordField(
        'Potwierdź hasło',
        validators=[
            DataRequired(),
            EqualTo('password', message='Hasła muszą się zgadzać'),
        ],
    )
    submit = SubmitField('Zresetuj hasło')


class BeneficjentForm(FlaskForm):
    """Form for adding or editing a beneficiary."""

    imie = StringField('Imię i nazwisko', validators=[DataRequired()])
    wojewodztwo = StringField('Województwo', validators=[DataRequired()])
    submit = SubmitField('Zapisz')


class DeleteForm(FlaskForm):
    """Simple confirmation form used for delete actions."""

    submit = SubmitField('Usuń')


class PromoteForm(FlaskForm):
    """Form used by admin to promote an instructor to admin."""

    submit = SubmitField('Nadaj admina')


class UserEditForm(FlaskForm):
    """Form for admin to edit instructor accounts."""

    full_name = StringField('Imię i nazwisko', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Zapisz')


class SettingsForm(FlaskForm):
    """Form for editing application configuration."""

    mail_server = StringField('Serwer SMTP')
    mail_port = IntegerField('Port SMTP', validators=[DataRequired()])
    mail_username = StringField('Użytkownik SMTP')
    mail_password = PasswordField('Hasło SMTP')
    timezone = StringField('Strefa czasowa')
    submit = SubmitField('Zapisz')
