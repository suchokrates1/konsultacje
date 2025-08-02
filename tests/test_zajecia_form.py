import pytest
from wtforms.validators import ValidationError
from app.forms import ZajeciaForm


def test_invalid_time_range_raises_error(app):
    """ZajeciaForm should raise ValidationError when end time precedes start."""
    with app.test_request_context('/', method='POST'):
        form = ZajeciaForm(
            data={
                'data': '2023-01-01',
                'godzina_od': '10:00',
                'godzina_do': '09:00',
                'beneficjenci': 1,
            }
        )
        form.beneficjenci.choices = [(1, 'Test')]
        with pytest.raises(ValidationError):
            form.validate()
        assert form.godzina_do.errors
