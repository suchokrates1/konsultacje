from app.forms import ZajeciaForm


def test_invalid_time_range_returns_error(app):
    """Form.validate should return False and set an error for invalid times."""
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
        assert not form.validate()
        assert form.godzina_do.errors
