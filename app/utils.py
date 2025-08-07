from flask import flash, abort
from functools import wraps

def flash_success(message):
    flash(message, 'success')

def flash_error(message):
    flash(message, 'danger')

def get_object_or_404(model, id):
    obj = model.query.get(id)
    if obj is None:
        abort(404)
    return obj

def validate_form(form):
    if form.validate_on_submit():
        return True
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", "danger")
    return False
