import re

def test_register_required_field_errors(client):
    response = client.post('/register', data={}, follow_redirects=True)
    text = response.get_data(as_text=True)
    errors = re.findall(r'<div class="text-danger">(.*?)</div>', text)
    # Expect four required field errors: full_name, email, password, confirm
    assert errors.count('This field is required.') >= 4


def test_register_password_mismatch_error(client):
    response = client.post(
        '/register',
        data={
            'full_name': 'user',
            'email': 'user@example.com',
            'password': 'secret',
            'confirm': 'different',
        },
        follow_redirects=True,
    )
    text = response.get_data(as_text=True)
    errors = re.findall(r'<div class="text-danger">(.*?)</div>', text)
    assert 'Hasła muszą się zgadzać' in errors
