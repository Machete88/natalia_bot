"""Tests fuer ErrorCorrectionEngine."""
import pytest
from services.error_correction import analyze_errors, ErrorCorrectionEngine


def test_no_errors_in_correct_german():
    result = analyze_errors("Ich bin ein Student.")
    assert not result.has_errors


def test_detects_conjugation_error_ich_ist():
    result = analyze_errors("ich ist muede")
    assert result.has_errors
    cats = [h.category for h in result.hints]
    assert "Konjugation" in cats


def test_detects_conjugation_error_du_bin():
    result = analyze_errors("du bin gross")
    cats = [h.category for h in result.hints]
    assert "Konjugation" in cats


def test_detects_umlaut_ae():
    result = analyze_errors("ich habe ae gegessen")
    cats = [h.category for h in result.hints]
    assert "Umlaut" in cats


def test_detects_umlaut_ue():
    result = analyze_errors("ich moechte Kaffee trinken, bitte schoen, fuer mich ue")
    cats = [h.category for h in result.hints]
    assert "Umlaut" in cats


def test_russian_text_no_errors():
    result = analyze_errors("Привет, как дела?")
    assert not result.has_errors


def test_to_prompt_context_format():
    result = analyze_errors("ich ist hier")
    ctx = result.to_prompt_context()
    assert "Ошибки" in ctx
    assert "Konjugation" in ctx


def test_no_errors_returns_empty_prompt_context():
    result = analyze_errors("Guten Morgen!")
    assert result.to_prompt_context() == ""


def test_multiple_errors():
    result = analyze_errors("ich ist hier und ae ue")
    assert len(result.hints) >= 2
