"""Einfaches Passwort-System fuer das Admin-Dashboard.

Passwort wird in .env gesetzt:
  ADMIN_DASHBOARD_PASSWORD=meinpasswort

Wenn nicht gesetzt, ist das Dashboard NUR lokal (127.0.0.1) zugaenglich.
"""
from __future__ import annotations
import os
import secrets
from functools import wraps
from flask import request, Response

_SESSION_TOKENS: set[str] = set()


def _get_password() -> str | None:
    return os.getenv("ADMIN_DASHBOARD_PASSWORD", None)


def _is_local_request() -> bool:
    return request.remote_addr in ("127.0.0.1", "::1", "localhost")


def require_auth(f):
    """Decorator: Authentifizierung erforderlich wenn ADMIN_DASHBOARD_PASSWORD gesetzt."""
    @wraps(f)
    def decorated(*args, **kwargs):
        pwd = _get_password()
        if not pwd:
            # Kein Passwort gesetzt -> nur lokaler Zugriff
            if not _is_local_request():
                return Response("Kein Zugriff. Nur lokal erreichbar.", 403)
            return f(*args, **kwargs)

        # Token-basierte Session (in-memory)
        token = request.cookies.get("admin_token")
        if token and token in _SESSION_TOKENS:
            return f(*args, **kwargs)

        # Basic Auth Fallback
        auth = request.authorization
        if auth and auth.password == pwd:
            return f(*args, **kwargs)

        return Response(
            "Admin-Bereich. Bitte einloggen.",
            401,
            {"WWW-Authenticate": 'Basic realm="natalia_bot Admin"'},
        )
    return decorated
