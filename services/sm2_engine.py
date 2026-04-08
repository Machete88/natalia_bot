"""SM-2 Spaced-Repetition-Algorithmus.

Original-Algorithmus von P.A. Wozniak (SuperMemo 2).
Qualitaet q:
  5 - perfekte Antwort
  4 - korrekt, kleine Zögerung
  3 - korrekt mit Muehe
  2 - falsch, aber die richtige Antwort war fast da
  1 - falsch, richtige Antwort war bekannt
  0 - komplett falsch / kein Versuch
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SM2Result:
    """Ergebnis einer SM-2-Berechnung."""
    interval_days: int       # Tage bis zur naechsten Wiederholung
    ease_factor: float       # Ease-Faktor (>= 1.3)
    repetitions: int         # Anzahl erfolgreicher Wiederholungen in Folge
    next_review_date: str    # ISO-Datum (YYYY-MM-DD)
    status: str              # 'new' | 'learning' | 'mastered'


MIN_EASE = 1.3
DEFAULT_EASE = 2.5


def sm2_update(
    quality: int,
    ease_factor: float = DEFAULT_EASE,
    interval_days: int = 0,
    repetitions: int = 0,
    today: date | None = None,
) -> SM2Result:
    """Berechnet neues Intervall und Ease-Faktor nach SM-2.

    Args:
        quality:      Antwortqualitaet 0-5 (>= 3 gilt als korrekt)
        ease_factor:  Aktueller Ease-Faktor des Items
        interval_days: Aktuelles Intervall in Tagen
        repetitions:  Anzahl bisheriger erfolgreicher Wdh. in Folge
        today:        Datum fuer next_review_date (Standard: heute)
    """
    today = today or date.today()

    if quality < 3:
        # Falsche Antwort: Wiederholungen und Intervall zuruecksetzen
        repetitions = 0
        interval_days = 1
    else:
        # Richtige Antwort
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = round(interval_days * ease_factor)

        repetitions += 1

    # Ease-Faktor anpassen
    ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease_factor = max(MIN_EASE, ease_factor)

    # Status bestimmen
    if repetitions == 0:
        status = "new"
    elif repetitions >= 5 and interval_days >= 21:
        status = "mastered"
    else:
        status = "learning"

    next_review = today + timedelta(days=interval_days)

    return SM2Result(
        interval_days=interval_days,
        ease_factor=round(ease_factor, 4),
        repetitions=repetitions,
        next_review_date=next_review.isoformat(),
        status=status,
    )


def bool_to_quality(correct: bool, hesitated: bool = False) -> int:
    """Konvertiert einfaches richtig/falsch in SM-2-Qualitaet.

    Fuer Stellen im Code die noch bool verwenden (Rueckwaertskompatibilitaet).
    """
    if correct and not hesitated:
        return 4
    if correct and hesitated:
        return 3
    return 1
