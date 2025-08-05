from app.forms import ZajeciaForm


def test_invalid_time_range_returns_error(app):
    """Form.validate should return False and set an error for invalid times."""
    with app.test_request_context('/', method='POST'):
        form = ZajeciaForm(
            data={
                'data': '2023-01-01',
                'godzina_od': '10:00',
                'godzina_do': '09:00',
                'specjalista': 'spec',
                'beneficjenci': 1,
            }
        )
        form.beneficjenci.choices = [(1, 'Test')]
        assert not form.validate()
        assert form.godzina_do.errors


def test_form_has_submit_send(app):
    """ZajeciaForm should include submit_send field."""
    with app.test_request_context('/'):
        form = ZajeciaForm()
        assert 'submit_send' in form._fields
