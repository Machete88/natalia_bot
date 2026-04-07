"""Tests fuer Aussprache-Bewertung."""
from __future__ import annotations
import pytest
from services.pronunciation import evaluate_pronunciation, format_feedback


def test_perfect_match():
    result = evaluate_pronunciation("Hallo", "Hallo")
    assert result["score"] == 100
    assert result["grade"] == "perfect"


def test_good_match():
    result = evaluate_pronunciation("Guten Morgen", "Guten Morgan")
    assert result["score"] >= 70
    assert result["grade"] in ("perfect", "good")


def test_poor_match():
    result = evaluate_pronunciation("Auf Wiedersehen", "xyz")
    assert result["score"] < 50
    assert result["grade"] == "try_again"


def test_case_insensitive():
    result = evaluate_pronunciation("hallo", "HALLO")
    assert result["score"] == 100


def test_format_feedback_contains_word():
    result = evaluate_pronunciation("Danke", "Danke")
    feedback = format_feedback(result, "imperator")
    assert "Danke" in feedback


def test_format_feedback_all_teachers():
    result = evaluate_pronunciation("Hallo", "xyz")
    fb = format_feedback(result, "imperator")
    assert len(fb) > 0
