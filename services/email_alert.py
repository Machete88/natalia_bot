"""E-Mail-Benachrichtigung wenn Natalia den Support-Modus aktiviert.

Konfiguration in .env:
  EMAIL_ENABLED=true
  EMAIL_FROM=dein@gmail.com
  EMAIL_TO=dein@gmail.com
  EMAIL_PASSWORD=app_passwort   # Gmail App-Passwort
  EMAIL_SMTP=smtp.gmail.com
  EMAIL_PORT=587
"""
from __future__ import annotations
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_email_config() -> dict:
    """Laedt E-Mail-Konfiguration aus .env / Umgebungsvariablen."""
    env = Path(".env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v
    return {
        "enabled":  os.getenv("EMAIL_ENABLED", "false").lower() == "true",
        "from":     os.getenv("EMAIL_FROM", ""),
        "to":       os.getenv("EMAIL_TO", ""),
        "password": os.getenv("EMAIL_PASSWORD", ""),
        "smtp":     os.getenv("EMAIL_SMTP", "smtp.gmail.com"),
        "port":     int(os.getenv("EMAIL_PORT", "587")),
    }


def send_support_alert(user_name: str) -> bool:
    """Sendet E-Mail-Benachrichtigung wenn Support-Modus aktiviert wird.
    Gibt True zurueck wenn erfolgreich, sonst False.
    """
    cfg = _load_email_config()
    if not cfg["enabled"]:
        logger.debug("E-Mail-Alerts deaktiviert (EMAIL_ENABLED=false)")
        return False
    if not cfg["from"] or not cfg["password"] or not cfg["to"]:
        logger.warning("E-Mail-Konfiguration unvollstaendig - Alert nicht gesendet")
        return False

    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"\U0001f514 natalia_bot: {user_name} braucht Hilfe!"
    msg["From"]    = cfg["from"]
    msg["To"]      = cfg["to"]

    text = (
        f"Support-Modus aktiviert\n"
        f"Nutzer: {user_name}\n"
        f"Zeit: {now}\n\n"
        f"Oeffne Telegram und antworte auf ihre Nachrichten.\n"
        f"Beende mit: /endsupport"
    )
    html = f"""
    <html><body style="font-family:system-ui,sans-serif;background:#f7f6f2;padding:2rem;">
      <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:2rem;border:1px solid #d4d1ca;">
        <h2 style="color:#01696f;margin-bottom:1rem;">&#x1f514; Support-Modus aktiv</h2>
        <p style="color:#28251d;"><strong>{user_name}</strong> hat das Codewort eingegeben.</p>
        <p style="color:#7a7974;margin-top:.5rem;">Zeit: {now}</p>
        <hr style="margin:1.5rem 0;border-color:#d4d1ca;">
        <p style="color:#28251d;">Oeffne Telegram und antworte auf ihre Nachrichten.<br>
        Alle Nachrichten werden an dich weitergeleitet.</p>
        <p style="margin-top:1rem;color:#7a7974;font-size:.85rem;">Beende mit: <code>/endsupport</code></p>
      </div>
    </body></html>
    """

    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(cfg["smtp"], cfg["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["from"], cfg["password"])
            server.sendmail(cfg["from"], cfg["to"], msg.as_string())
        logger.info("Support-Alert E-Mail gesendet an %s", cfg["to"])
        return True
    except Exception as e:
        logger.error("E-Mail-Versand fehlgeschlagen: %s", e)
        return False
