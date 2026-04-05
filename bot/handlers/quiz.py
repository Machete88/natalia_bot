"""Handler fuer /quiz - Vokabel-Quiz mit Antwort-Auswertung."""
from __future__ import annotations

import logging
import random
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

QUIZ_SESSION_KEY = "quiz_session"


@dataclass
class QuizSession:
    vocab_id: int
    word_de: str
    word_ru: str
    example_de: str
    correct_answer: str  # das deutsche Wort
    options: list = field(default_factory=list)  # 4 Optionen (Russisch -> Deutsch)
    score: int = 0
    total: int = 0


def _get_quiz_item(db_path: str, user_id: int, level: str) -> Optional[dict]:
    """Hole ein Vokabel-Item das noch nicht gemeistert wurde."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        # Bevorzuge Items im Status 'learning', dann 'new'
        row = conn.execute(
            """
            SELECT vi.id, vi.word_de, vi.word_ru, vi.example_de, vi.example_ru
            FROM vocab_items vi
            LEFT JOIN vocab_progress vp ON vi.id = vp.vocab_id AND vp.user_id = ?
            WHERE vi.level = ?
              AND (vp.status IS NULL OR vp.status != 'mastered')
            ORDER BY
              CASE WHEN vp.status = 'learning' THEN 0
                   WHEN vp.status IS NULL THEN 1
                   ELSE 2 END,
              RANDOM()
            LIMIT 1
            """,
            (user_id, level),
        ).fetchone()

        if not row:
            # Fallback: beliebiges Item aus der gesamten Datenbank
            row = conn.execute(
                "SELECT id, word_de, word_ru, example_de, example_ru FROM vocab_items ORDER BY RANDOM() LIMIT 1"
            ).fetchone()

        if not row:
            return None

        # 3 Distraktoren
        distractors = conn.execute(
            """
            SELECT word_de FROM vocab_items
            WHERE id != ?
            ORDER BY RANDOM() LIMIT 3
            """,
            (row["id"],),
        ).fetchall()

        options = [row["word_de"]] + [d["word_de"] for d in distractors]
        random.shuffle(options)

        return {
            "vocab_id": row["id"],
            "word_de": row["word_de"],
            "word_ru": row["word_ru"],
            "example_de": row["example_de"] or "",
            "options": options,
        }


def _update_vocab_progress(db_path: str, user_id: int, vocab_id: int, correct: bool) -> str:
    """Aktualisiert den Status. Gibt neuen Status zurueck."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT status, correct_streak FROM vocab_progress WHERE user_id=? AND vocab_id=?",
            (user_id, vocab_id),
        ).fetchone()

        if row:
            streak = (row["correct_streak"] + 1) if correct else 0
            status = "mastered" if streak >= 3 else "learning"
            conn.execute(
                "UPDATE vocab_progress SET status=?, correct_streak=?, last_seen=datetime('now') WHERE user_id=? AND vocab_id=?",
                (status, streak, user_id, vocab_id),
            )
        else:
            streak = 1 if correct else 0
            status = "learning"
            conn.execute(
                "INSERT INTO vocab_progress (user_id, vocab_id, status, correct_streak) VALUES (?,?,?,?)",
                (user_id, vocab_id, status, streak),
            )
        return status


QUIZ_QUESTION_TPLS = {
    "vitali": "\U0001f914 *Как по-немецки:* {word_ru}\n\n{options_text}\n\nПросто ответь цифрой 1-4!",
    "dering": "\U0001f4dd *Переведите:* {word_ru}\n\n{options_text}",
    "imperator": "\U0001f525 {word_ru}\n\n{options_text}",
}

CORRECT_TPLS = {
    "vitali": [
        "\u2705 Верно! *{word_de}* \U0001f44f",
        "\u2705 Отлично! *{word_de}* — молодец!",
        "\U0001f31f Да! *{word_de}*. Продолжай!",
    ],
    "dering": [
        "\u2705 *{word_de}* — верно.",
        "\u2705 Правильно. *{word_de}*",
    ],
    "imperator": [
        "\u2705 *{word_de}*.",
        "\u2705 Верно. *{word_de}*.",
    ],
}

WRONG_TPLS = {
    "vitali": [
        "\u274c Нет, но не беда! Правильный ответ: *{word_de}*\n\u2014 запомни: _{example_de}_",
        "\u274c Почти! Правильно: *{word_de}*\n\u2014 пример: _{example_de}_",
    ],
    "dering": [
        "\u274c Неверно. Правильный ответ: *{word_de}*.",
        "\u274c Ошибка. *{word_de}* — _{example_de}_",
    ],
    "imperator": [
        "\u274c Нет. *{word_de}*.",
        "\u274c Ошибка. *{word_de}*.",
    ],
}


def _make_options_text(options: list) -> str:
    return "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))


async def handle_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Startet eine neue Quiz-Runde oder wertet die Antwort aus."""
    services = context.bot_data.get("services", {})
    settings = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    if not user_repo or not settings:
        await update.message.reply_text("Сервис врененно недоступен.")
        return

    user = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    teacher = user_repo.get_teacher(user_id)
    level = user_repo.get_level(user_id)

    # Hole Quiz-Session aus user_data
    session: Optional[QuizSession] = context.user_data.get(QUIZ_SESSION_KEY)
    text = update.message.text.strip() if update.message.text else ""

    # Antwort auswerten, wenn Session aktiv und Antwort 1-4
    if session and text in {"1", "2", "3", "4"}:
        chosen_idx = int(text) - 1
        if 0 <= chosen_idx < len(session.options):
            chosen = session.options[chosen_idx]
            correct = chosen == session.correct_answer

            # Progress aktualisieren
            new_status = _update_vocab_progress(
                settings.database_path, user_id, session.vocab_id, correct
            )

            session.total += 1
            if correct:
                session.score += 1

            # Rueckmeldung
            pool = CORRECT_TPLS[teacher] if correct else WRONG_TPLS[teacher]
            feedback = random.choice(pool).format(
                word_de=session.correct_answer,
                example_de=session.example_de,
            )
            mastered_note = " \U0001f3c6" if new_status == "mastered" else ""
            await update.message.reply_text(
                f"{feedback}{mastered_note}\n\nОчки: {session.score}/{session.total}",
                parse_mode="Markdown",
            )

            # Automatisch naechste Frage
            context.user_data.pop(QUIZ_SESSION_KEY, None)
            await _send_next_question(update, context, settings.database_path, user_id, teacher, level)
            return

    # /quiz Befehl: neue Frage stellen
    context.user_data.pop(QUIZ_SESSION_KEY, None)
    score = context.user_data.get("quiz_score", 0)
    total = context.user_data.get("quiz_total", 0)
    await _send_next_question(update, context, settings.database_path, user_id, teacher, level, score=score, total=total)


async def _send_next_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_path: str,
    user_id: int,
    teacher: str,
    level: str,
    score: int = 0,
    total: int = 0,
) -> None:
    item = _get_quiz_item(db_path, user_id, level)
    if not item:
        await update.message.reply_text(
            "\U0001f389 Все слова пройдены! Приходи позже."
        )
        return

    session = QuizSession(
        vocab_id=item["vocab_id"],
        word_de=item["word_de"],
        word_ru=item["word_ru"],
        example_de=item["example_de"],
        correct_answer=item["word_de"],
        options=item["options"],
        score=score,
        total=total,
    )
    context.user_data[QUIZ_SESSION_KEY] = session

    tpl = QUIZ_QUESTION_TPLS.get(teacher, QUIZ_QUESTION_TPLS["vitali"])
    options_text = _make_options_text(item["options"])
    question = tpl.format(word_ru=item["word_ru"], options_text=options_text)
    await update.message.reply_text(question, parse_mode="Markdown")
