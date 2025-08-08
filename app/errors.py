"""Application-wide error handlers."""

from flask import render_template

from . import db


def register_error_handlers(app):
    """Register standard error handlers on the given app."""

    @app.errorhandler(404)
    def not_found_error(error):  # pragma: no cover - simple rendering
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):  # pragma: no cover - simple rendering
        db.session.rollback()
        return render_template("500.html"), 500

