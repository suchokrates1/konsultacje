from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField, SubmitField, DateField, TimeField
from wtforms.validators import DataRequired
from wtforms.widgets import ListWidget, CheckboxInput

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class ZajeciaForm(FlaskForm):
    data = DateField('Data konsultacji', validators=[DataRequired()])
    godzina_od = TimeField('Godzina od', validators=[DataRequired()])
    godzina_do = TimeField('Godzina do', validators=[DataRequired()])
    beneficjenci = MultiCheckboxField('Beneficjenci', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Zapisz zajęcia')
