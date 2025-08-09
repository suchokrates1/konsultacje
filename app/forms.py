"""WTForms used to validate and handle user input."""

from flask_wtf import FlaskForm
from wtforms import (
    SelectMultipleField,
    SelectField,
    SubmitField,
    DateField,
    TimeField,
    StringField,
    PasswordField,
    EmailField,
    IntegerField,
    BooleanField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Optional,
    NumberRange,
)
import pytz
from wtforms.widgets import ListWidget, CheckboxInput

WOJEWODZTWA = [
    'Dolnoslaskie',
    'Kujawsko-Pomorskie',
    'Lubelskie',
    'Lubuskie',
    'Lodzkie',
    'Malopolskie',
    'Mazowieckie',
    'Opolskie',
    'Podkarpackie',
    'Podlaskie',
    'Pomorskie',
    'Slaskie',
    'Swietokrzyskie',
    'Warminsko-Mazurskie',
    'Wielkopolskie',
    'Zachodniopomorskie',
]

# Common time zones used to populate the settings dropdown.
TIMEZONE_CHOICES = [(tz, tz) for tz in pytz.common_timezones]


class MultiCheckboxField(SelectMultipleField):
    """Multiple selection field rendered as a list of checkboxes."""

    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class LoginForm(FlaskForm):
    """Form used by users to authenticate to the application."""

    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember_me = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj się')


class ZajeciaForm(FlaskForm):
    """Form for scheduling a consultation session."""

    data = DateField('Data konsultacji', validators=[DataRequired()])
    godzina_od = TimeField('Godzina od', validators=[DataRequired()])
    godzina_do = TimeField('Godzina do', validators=[DataRequired()])
    specjalista = StringField('Konsultacje z:', validators=[DataRequired()])
    beneficjenci = SelectField(
        'Beneficjent', coerce=int, validators=[DataRequired()]
    )
    save = SubmitField('Zapisz')
    submit_send = SubmitField('Zapisz i wyślij')

    def validate(self, extra_validators=None):
        # pragma: no cover - custom logic
        """Ensure the end time is later than the start time."""
        if not super().validate(extra_validators):
            return False
        if self.godzina_do.data <= self.godzina_od.data:
            message = (
                'Godzina zakończenia musi być późniejsza niż '
                'godzina rozpoczęcia.'
            )
            self.godzina_do.errors.append(message)
            return False
        return True


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


class PasswordChangeForm(FlaskForm):
    """Form for authenticated users to change their password."""

    old_password = PasswordField('Aktualne hasło', validators=[DataRequired()])
    new_password = PasswordField('Nowe hasło', validators=[DataRequired()])
    confirm = PasswordField(
        'Potwierdź hasło',
        validators=[
            DataRequired(),
            EqualTo('new_password', message='Hasła muszą się zgadzać'),
        ],
    )
    submit = SubmitField('Zmień hasło')


class UserSettingsForm(FlaskForm):
    """Form allowing users to update their details and password."""

    email = EmailField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Imię i nazwisko', validators=[DataRequired()])
    default_duration = IntegerField(
        'Domyślny czas trwania (min)',
        validators=[DataRequired(), NumberRange(min=1)],
    )
    session_type = StringField('Konsultacje z', validators=[Optional()])
    document_recipient_email = EmailField(
        'Email odbiorcy dokumentów',
        validators=[Optional(), Email()],
    )
    old_password = PasswordField(
        'Aktualne hasło', validators=[Optional()]
    )
    new_password = PasswordField(
        'Nowe hasło', validators=[Optional()]
    )
    confirm = PasswordField(
        'Potwierdź hasło',
        validators=[
            Optional(),
            EqualTo('new_password', message='Hasła muszą się zgadzać'),
        ],
    )
    submit = SubmitField('Zapisz')

    def validate(self, extra_validators=None):
        """Ensure both password fields are provided together."""
        rv = super().validate(extra_validators)
        if self.new_password.data or self.confirm.data:
            if not self.new_password.data or not self.confirm.data:
                message = 'Oba pola hasła są wymagane'
                if not self.new_password.data:
                    self.new_password.errors.append(message)
                if not self.confirm.data:
                    self.confirm.errors.append(message)
                rv = False
        return rv


class BeneficjentForm(FlaskForm):
    """Form for adding or editing a beneficiary."""

    imie = StringField('Imię i nazwisko', validators=[DataRequired()])
    wojewodztwo = SelectField(
        'Województwo',
        choices=[(w, w) for w in WOJEWODZTWA],
        validators=[DataRequired()],
    )
    submit = SubmitField('Zapisz')


class DeleteForm(FlaskForm):
    """Simple confirmation form used for delete actions."""

    submit = SubmitField('Usuń')


class PromoteForm(FlaskForm):
    """Form used by admin to promote an instructor to admin."""

    submit = SubmitField('Nadaj admina')


class DemoteForm(FlaskForm):
    """Form used by superadmin to demote an admin to instructor."""

    submit = SubmitField('Degraduj')


class ConfirmForm(FlaskForm):
    """Form used by admin to confirm a new instructor's account."""

    submit = SubmitField('Potwierdź rejestrację')


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
    mail_use_tls = BooleanField('Użyj TLS')
    mail_use_ssl = BooleanField('Użyj SSL')
    admin_email = EmailField(
        'Email administratora', validators=[Optional(), Email()]
    )
    sender_name = StringField('Nazwa nadawcy')
    timezone = SelectField('Strefa czasowa', choices=TIMEZONE_CHOICES)
    submit = SubmitField('Zapisz')
    send_test = SubmitField('Wyślij test')
