"""Tests fuer den SM-2-Algorithmus."""
from datetime import date

import pytest

from services.sm2_engine import SM2Result, bool_to_quality, sm2_update


class TestSM2Update:
    def test_first_correct_answer_q4(self):
        result = sm2_update(quality=4, today=date(2026, 1, 1))
        assert result.interval_days == 1
        assert result.repetitions == 1
        assert result.status == "learning"
        assert result.next_review_date == "2026-01-02"

    def test_second_correct_answer(self):
        result = sm2_update(quality=4, interval_days=1, repetitions=1, today=date(2026, 1, 1))
        assert result.interval_days == 6
        assert result.repetitions == 2

    def test_third_correct_answer_uses_ease(self):
        result = sm2_update(quality=4, ease_factor=2.5, interval_days=6, repetitions=2, today=date(2026, 1, 1))
        assert result.interval_days == 15  # 6 * 2.5 = 15
        assert result.repetitions == 3

    def test_wrong_answer_resets(self):
        result = sm2_update(quality=1, ease_factor=2.5, interval_days=15, repetitions=3, today=date(2026, 1, 1))
        assert result.interval_days == 1
        assert result.repetitions == 0
        assert result.status in ("new", "learning")

    def test_ease_factor_not_below_min(self):
        result = sm2_update(quality=0, ease_factor=1.4, today=date(2026, 1, 1))
        assert result.ease_factor >= 1.3

    def test_mastered_after_many_repetitions(self):
        result = sm2_update(quality=5, ease_factor=2.8, interval_days=18, repetitions=4, today=date(2026, 1, 1))
        # 18 * 2.8 = 50.4 Tage -> mastered
        assert result.status == "mastered"

    def test_quality_5_increases_ease(self):
        result = sm2_update(quality=5, ease_factor=2.5, interval_days=0, repetitions=0)
        assert result.ease_factor > 2.5

    def test_quality_3_neutral_ease(self):
        result = sm2_update(quality=3, ease_factor=2.5, interval_days=0, repetitions=0)
        # Qualitaet 3: delta = 0.1 - 2*(0.08+2*0.02) = 0.1 - 0.24 = -0.14 -> leicht kleiner
        assert result.ease_factor < 2.5


class TestBoolToQuality:
    def test_correct_not_hesitated(self):
        assert bool_to_quality(True, hesitated=False) == 4

    def test_correct_hesitated(self):
        assert bool_to_quality(True, hesitated=True) == 3

    def test_wrong(self):
        assert bool_to_quality(False) == 1


class TestSM2NextReviewDate:
    def test_date_advances_by_interval(self):
        result = sm2_update(quality=4, interval_days=6, repetitions=1, today=date(2026, 4, 1))
        # interval = 6 * 2.5 = 15 Tage
        assert result.next_review_date == "2026-04-16"
