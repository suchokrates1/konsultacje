"""Helpers for project context and scoping."""

from datetime import UTC, datetime

from flask import request

from . import db
from .models import ProjectStatus, Projekt


def get_aktywny_projekt():
    """Return the currently active project or ``None``."""
    return Projekt.query.filter_by(status=ProjectStatus.AKTYWNY).first()


def ustaw_jako_aktywny(projekt):
    """Archive the current active project and activate *projekt*."""
    current = get_aktywny_projekt()
    if current and current.id != projekt.id:
        current.status = ProjectStatus.ARCHIWUM
        current.zarchiwizowano = datetime.now(UTC)
    projekt.status = ProjectStatus.AKTYWNY
    projekt.zarchiwizowano = None
    db.session.commit()


def resolve_admin_projekt():
    """Return the project selected in admin views (defaults to active)."""
    projekt_id = request.args.get("projekt_id", type=int)
    if projekt_id:
        projekt = db.session.get(Projekt, projekt_id)
        if projekt:
            return projekt
    aktywny = get_aktywny_projekt()
    if aktywny:
        return aktywny
    return Projekt.query.order_by(Projekt.utworzono.desc()).first()
