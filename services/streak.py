"""Streak-System: zaehlt aufeinanderfolgende Lerntage.

Streaks werden in user_preferences gespeichert:
  streak_count  -> aktuelle Streak-Zahl
  streak_last   -> letztes Datum (YYYY-MM-DD)
  streak_best   -> bester Streak je

Wird nach jeder /lesson oder /quiz aufgerufen.
"""
from __future__ import annotations
import logging
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)


def update_streak(db, user_id: int) -> dict:
    """Aktualisiert Streak fuer user_id. Gibt {'count': N, 'is_new': bool, 'best': N} zurueck."""
    today = date.today().isoformat()

    def _get(key, default="0"):
        row = db.execute(
            "SELECT value FROM user_preferences WHERE user_id=? AND key=?",
            (user_id, key)
        ).fetchone()
        return row[0] if row else default

    def _set(key, value):
        db.execute(
            "INSERT OR REPLACE INTO user_preferences (user_id, key, value) VALUES (?,?,?)",
            (user_id, key, str(value))
        )

    last   = _get("streak_last", "")
    count  = int(_get("streak_count", "0"))
    best   = int(_get("streak_best", "0"))
    is_new = False

    if last == today:
        # Heute schon gelernt - kein Update noetig
        pass
    elif last == (date.today() - timedelta(days=1)).isoformat():
        # Gestern gelernt -> Streak fortsetzen
        count += 1
        is_new = count > best
        if is_new:
            best = count
        _set("streak_count", count)
        _set("streak_last", today)
        _set("streak_best", best)
    else:
        # Streak unterbrochen
        count = 1
        _set("streak_count", 1)
        _set("streak_last", today)
        if best == 0:
            best = 1
            _set("streak_best", 1)

    try:
        db.commit()
    except Exception:
        pass

    return {"count": count, "is_new": is_new, "best": best}


def get_streak(db, user_id: int) -> dict:
    """Gibt aktuellen Streak zurueck ohne zu aktualisieren."""
    def _get(key, default="0"):
        row = db.execute(
            "SELECT value FROM user_preferences WHERE user_id=? AND key=?",
            (user_id, key)
        ).fetchone()
        return row[0] if row else default

    count = int(_get("streak_count", "0"))
    best  = int(_get("streak_best", "0"))
    last  = _get("streak_last", "")

    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    active    = last in (today, yesterday)

    return {"count": count if active else 0, "best": best, "last": last, "active": active}


def streak_emoji(count: int) -> str:
    """Gibt passendes Emoji fuer Streak-Groesse zurueck."""
    if count >= 30: return "\U0001f3c6"
    if count >= 14: return "\U0001f525"
    if count >= 7:  return "\U0001f4aa"
    if count >= 3:  return "\U0001f31f"
    return "\u2728"


def streak_message(count: int, teacher: str, is_new_best: bool = False) -> str:
    """Generiert Streak-Nachricht passend zum Lehrer."""
    emoji = streak_emoji(count)

    if is_new_best:
        msgs = {
            "vitali":    f"{emoji} Neuer Rekord! {count} Tage in Folge! Du bist grossartig! \U0001f389",
            "dering":    f"{emoji} Rekord: {count} Tage! Weiter so!",
            "imperator": f"{emoji} {count} TAGE. NEUER REKORD. WEITER.",
        }
        return msgs.get(teacher, msgs["vitali"])

    if count == 1:
        msgs = {
            "vitali":    "\u2728 Erster Tag! Jeden Tag ein bisschen - das ist der Schlussel!",
            "dering":    "\u2728 Tag 1. Gut gemacht.",
            "imperator": "\U0001f525 Tag 1. Erst der Anfang.",
        }
        return msgs.get(teacher, msgs["vitali"])

    milestones = {7: "eine Woche", 14: "zwei Wochen", 30: "einen Monat", 100: "100 Tage"}
    for milestone, label in milestones.items():
        if count == milestone:
            msgs = {
                "vitali":    f"{emoji} {label} hintereinander! Das ist wirklich beeindruckend! \U0001f389",
                "dering":    f"{emoji} {label}! Sehr gut.",
                "imperator": f"{emoji} {label}! Respekt.",
            }
            return msgs.get(teacher, msgs["vitali"])

    msgs = {
        "vitali":    f"{emoji} {count} Tage hintereinander! Weiter so!",
        "dering":    f"{emoji} Streak: {count} Tage.",
        "imperator": f"{emoji} {count} Tage. Nicht aufhoeren.",
    }
    return msgs.get(teacher, msgs["vitali"])


def streak_calendar(db, user_id: int, days: int = 7) -> str:
    """Gibt 7-Tage-Kalender als Text zurueck.
    Gruenes Quadrat = gelernt, graues = nicht gelernt.
    """
    today = date.today()
    rows = db.execute(
        "SELECT DATE(last_seen) as d FROM vocab_progress WHERE user_id=? AND last_seen IS NOT NULL GROUP BY DATE(last_seen)",
        (user_id,)
    ).fetchall()
    learned_days = {row[0] for row in rows}

    calendar = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        if d in learned_days:
            calendar.append("\U0001f7e9")  # gruen
        else:
            calendar.append("\u2b1c")      # grau

    return " ".join(calendar)
