"""ErrorCorrectionEngine — klassifiziert deutsche Sprachfehler vor dem LLM-Call.

Gibt dem Imperator-Prompt praezise Fehler-Hinweise statt ihn raten zu lassen.

Klassen:
- ArtikelFehler:   falscher/fehlender Artikel (der/die/das)
- KasussFehler:    falscher Kasus (Akkusativ statt Nominativ etc.)
- WortstellungsFehler: falsche Verbstellung
- KonjugationsFehler: falsche Verbform
- UmlautFehler:    fehlendes Umlaut (ae statt ae, ue statt ue etc.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# Artikel-Map: Nominativ
ARTIKEL = {
    "der", "die", "das", "ein", "eine", "einen", "einem", "einer", "des", "den"
}

# Haeufige Verben und ihre korrekte Konjugation (Praesenss, Singular)
KONJUG_RULES: dict[str, dict[str, str]] = {
    "sein":   {"ich": "bin",  "du": "bist", "er": "ist",  "wir": "sind", "sie": "sind"},
    "haben":  {"ich": "habe", "du": "hast", "er": "hat",  "wir": "haben", "sie": "haben"},
    "werden": {"ich": "werde","du": "wirst","er": "wird", "wir": "werden","sie": "werden"},
}

# Umlaut-Fehler Muster: Nutzer schreibt ASCII-Version
UMLAUT_PATTERNS = [
    (re.compile(r'\bae\b'), 'ae → ä'),
    (re.compile(r'\boe\b'), 'oe → ö'),
    (re.compile(r'\bue\b'), 'ue → ü'),
    (re.compile(r'\bss\b'), 'ss → ß (ggf.)'),
]


@dataclass
class CorrectionHint:
    category: str   # z.B. "Artikel", "Konjugation", "Wortstellung"
    original: str   # was der Nutzer schrieb
    suggestion: str # was korrekt waere
    rule: str       # kurze Erklarung fuer den LLM


@dataclass
class CorrectionResult:
    has_errors:   bool
    hints:        List[CorrectionHint] = field(default_factory=list)
    error_summary: str = ""  # kompakter String fuer Prompt

    def to_prompt_context(self) -> str:
        if not self.has_errors:
            return ""
        lines = ["[Ошибки Наташи — исправь каждую с правилом:"]
        for h in self.hints:
            lines.append(f"  • {h.category}: '{h.original}' → '{h.suggestion}' ({h.rule})")
        lines.append("]")
        return "\n".join(lines)


class ErrorCorrectionEngine:
    """Analysiert deutschen Text und gibt strukturierte Korrektur-Hinweise zurueck."""

    def analyze(self, text: str) -> CorrectionResult:
        hints: List[CorrectionHint] = []

        hints.extend(self._check_umlauts(text))
        hints.extend(self._check_verb_position(text))
        hints.extend(self._check_conjugation(text))

        return CorrectionResult(
            has_errors=len(hints) > 0,
            hints=hints,
            error_summary="; ".join(f"{h.category}: {h.original}→{h.suggestion}" for h in hints),
        )

    def _check_umlauts(self, text: str) -> List[CorrectionHint]:
        hints = []
        lower = text.lower()
        for pattern, label in UMLAUT_PATTERNS:
            if pattern.search(lower):
                orig, sug = label.split(" → ")
                hints.append(CorrectionHint(
                    category="Umlaut",
                    original=orig,
                    suggestion=sug,
                    rule="Deutsche Umlaute bitte direkt schreiben (ä/ö/ü/ß)",
                ))
        return hints

    def _check_verb_position(self, text: str) -> List[CorrectionHint]:
        """Prueft ob Verb in einfachem Aussagesatz an Position 2 steht."""
        hints = []
        sentences = re.split(r'[.!?]', text)
        for sent in sentences:
            words = sent.strip().split()
            if len(words) < 3:
                continue
            # Heuristik: wenn letztes Wort ein bekanntes Hilfsverb ist → Fehler
            last = words[-1].lower()
            known_verbs = {"bin", "ist", "bist", "sind", "hat", "habe", "hast", "haben"}
            if last in known_verbs and len(words) > 2:
                hints.append(CorrectionHint(
                    category="Wortstellung",
                    original=sent.strip(),
                    suggestion=f"Verb '{last}' gehoert an Position 2",
                    rule="Im deutschen Aussagesatz steht das Verb immer auf Position 2",
                ))
                break  # max 1 Wortstellungsfehler pro Text
        return hints

    def _check_conjugation(self, text: str) -> List[CorrectionHint]:
        """Sucht nach typischen Konjugationsfehlern (ich ist, du bin etc.)."""
        hints = []
        lower = text.lower()
        bad_combos = [
            ("ich ist",  "ich bin",  "'sein': ich → bin"),
            ("du bin",   "du bist",  "'sein': du → bist"),
            ("er bin",   "er ist",   "'sein': er → ist"),
            ("ich hat",  "ich habe", "'haben': ich → habe"),
            ("du habe",  "du hast",  "'haben': du → hast"),
            ("er habe",  "er hat",   "'haben': er → hat"),
        ]
        for wrong, correct, rule in bad_combos:
            if wrong in lower:
                hints.append(CorrectionHint(
                    category="Konjugation",
                    original=wrong,
                    suggestion=correct,
                    rule=rule,
                ))
        return hints


# Singleton fuer Import
_engine = ErrorCorrectionEngine()


def analyze_errors(text: str) -> CorrectionResult:
    """Convenience-Funktion."""
    return _engine.analyze(text)
