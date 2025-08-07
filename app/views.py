from flask import render_template, redirect, url_for
from app import app
from app.forms import RegisterForm
from app.models import Zajecia
from app.utils import flash_success, flash_error, get_object_or_404, validate_form

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if validate_form(form):
        # ...existing code for creating user...
        flash_success("Konto zostało utworzone. Sprawdź email, aby potwierdzić rejestrację.")
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/zajecia/<int:zajecia_id>')
def zajecia_detail(zajecia_id):
    zajecia = get_object_or_404(Zajecia, zajecia_id)
    return render_template('zajecia_detail.html', zajecia=zajecia)

# Analogicznie używaj flash_success, flash_error, get_object_or_404, validate_form w innych widokach
