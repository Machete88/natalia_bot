"""Handler fuer /quiz — Vokabel-Quiz mit Inline-Keyboard-Antworten."""
from __future__ import annotations

import asyncio
import logging
import random
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

QUIZ_SESSION_KEY = "quiz_session"
_PAUSE_SECS      = 1.5   # kurze Pause zwischen Frage und naechster
_ROUNDS_PER_SESSION = 10  # Quiz-Session laeuft ueber 10 Fragen


@dataclass
class QuizSession:
    vocab_id:       int
    word_de:        str
    word_ru:        str
    example_de:     str
    correct_answer: str
    options:        list = field(default_factory=list)
    score:          int  = 0
    total:          int  = 0


# ---------------------------------------------------------------------------
# DB-Helpers
# ---------------------------------------------------------------------------

def _get_quiz_item(db_path: str, user_id: int, level: str) -> Optional[dict]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT vi.id, vi.word_de, vi.word_ru, vi.example_de
            FROM vocab_items vi
            LEFT JOIN vocab_progress vp ON vi.id = vp.vocab_id AND vp.user_id = ?
            WHERE vi.level = ?
              AND (vp.status IS NULL OR vp.status != 'mastered')
            ORDER BY
              CASE WHEN vp.status = 'learning' THEN 0
                   WHEN vp.status IS NULL      THEN 1
                   ELSE 2 END,
              RANDOM()
            LIMIT 1
            """,
            (user_id, level),
        ).fetchone()

        if not row:
            row = conn.execute(
                "SELECT id, word_de, word_ru, example_de FROM vocab_items ORDER BY RANDOM() LIMIT 1"
            ).fetchone()
        if not row:
            return None

        distractors = conn.execute(
            "SELECT word_de FROM vocab_items WHERE id != ? ORDER BY RANDOM() LIMIT 3",
            (row["id"],),
        ).fetchall()

        options = [row["word_de"]] + [d["word_de"] for d in distractors]
        random.shuffle(options)

        return {
            "vocab_id":  row["id"],
            "word_de":   row["word_de"],
            "word_ru":   row["word_ru"],
            "example_de":row["example_de"] or "",
            "options":   options,
        }


def _update_vocab_progress(db_path: str, user_id: int, vocab_id: int, correct: bool) -> str:
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
                "UPDATE vocab_progress SET status=?, correct_streak=?, last_seen=datetime('now') "
                "WHERE user_id=? AND vocab_id=?",
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


# ---------------------------------------------------------------------------
# Nachrichten-Templates
# ---------------------------------------------------------------------------

def _quiz_question_text(word_ru: str, score: int, total: int, rounds: int) -> str:
    progress = f"{total + 1}/{rounds}"
    return f"\U0001f525 *{word_ru}*\n\u2014 по-немецки? `[{progress}]`"


CORRECT_MSGS = [
    "\u2705 *{word_de}*. Правильно!",
    "\u2705 *{word_de}*. Точно.",
    "\u2705 Молодец. *{word_de}*.",
]

WRONG_MSGS = [
    "\u274c Нет. Правильно: *{word_de}*.\n\u2014 _{example}_",
    "\u274c Неверно. *{word_de}*. Запомни.",
]


def _make_keyboard(options: list) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for i, opt in enumerate(options):
        row.append(InlineKeyboardButton(f"{i+1}. {opt}", callback_data=f"quiz_{i+1}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

async def handle_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Startet oder setzt eine Quiz-Session fort (via /quiz Befehl)."""
    services  = context.bot_data.get("services", {})
    settings  = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    if not user_repo or not settings:
        await (update.message or update.callback_query.message).reply_text(
            "Сервис временно недоступен."
        )
        return

    user    = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    level   = user_repo.get_level(user_id)

    # Eventuell laufende Session abbrechen
    context.user_data.pop(QUIZ_SESSION_KEY, None)
    await _send_next_question(update, context, settings.database_path, user_id, level)


async def handle_quiz_inline(
    update: Update, context: ContextTypes.DEFAULT_TYPE, answer: str
) -> None:
    """Verarbeitet Inline-Keyboard Antwort."""
    services  = context.bot_data.get("services", {})
    settings  = context.bot_data.get("settings")
    user_repo = services.get("user_repo")

    if not user_repo or not settings:
        return

    user    = update.effective_user
    user_id = user_repo.get_or_create_user(user.id, user.first_name or "")
    level   = user_repo.get_level(user_id)

    session: Optional[QuizSession] = context.user_data.get(QUIZ_SESSION_KEY)
    if not session:
        await update.callback_query.edit_message_text(
            "Session abgelaufen. /quiz neu starten."
        )
        return

    chosen_idx = int(answer) - 1
    await _evaluate_answer(
        update, context, session, chosen_idx, settings, user_id, level
    )


async def _evaluate_answer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: QuizSession,
    chosen_idx: int,
    settings,
    user_id: int,
    level: str,
) -> None:
    chosen  = session.options[chosen_idx] if 0 <= chosen_idx < len(session.options) else ""
    correct = (chosen == session.correct_answer)

    new_status = _update_vocab_progress(
        settings.database_path, user_id, session.vocab_id, correct
    )
    session.total += 1
    if correct:
        session.score += 1

    template = random.choice(CORRECT_MSGS if correct else WRONG_MSGS)
    feedback = template.format(
        word_de=session.correct_answer,
        example=session.example_de,
    )
    mastered_badge = " \U0001f3c6 Выучено!" if new_status == "mastered" else ""
    score_line     = f"\n\u2014 {session.score}/{session.total} правильных"
    result_text    = f"{feedback}{mastered_badge}{score_line}"

    # Inline-Keyboard entfernen + Feedback anzeigen
    if update.callback_query:
        await update.callback_query.edit_message_text(result_text, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(result_text, parse_mode="Markdown")

    context.user_data.pop(QUIZ_SESSION_KEY, None)

    # Session-Ende?
    if session.total >= _ROUNDS_PER_SESSION:
        pct = int(session.score / session.total * 100)
        emoji = "\U0001f3c6" if pct >= 80 else "\U0001f4aa" if pct >= 50 else "\U0001f4da"
        summary = (
            f"{emoji} *Квиз завершён!*\n"
            f"Правильных: *{session.score}/{session.total}* ({pct}%)\n\n"
            f"/quiz — сыграть ещё раз"
        )
        msg_target = (
            update.callback_query.message if update.callback_query else update.message
        )
        if msg_target:
            await asyncio.sleep(_PAUSE_SECS)
            await msg_target.reply_text(summary, parse_mode="Markdown")
        return

    # Kurze Pause, dann naechste Frage
    await asyncio.sleep(_PAUSE_SECS)
    await _send_next_question(
        update, context, settings.database_path, user_id, level,
        score=session.score, total=session.total
    )


async def _send_next_question(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db_path: str,
    user_id: int,
    level: str,
    score: int = 0,
    total: int = 0,
) -> None:
    item = _get_quiz_item(db_path, user_id, level)

    target = (
        update.callback_query.message if update.callback_query
        else update.message
    )
    if not target:
        return

    if not item:
        await target.reply_text(
            "\U0001f3c6 Все слова выучены! Зайди позже."
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

    question = _quiz_question_text(item["word_ru"], score, total, _ROUNDS_PER_SESSION)
    keyboard = _make_keyboard(item["options"])
    await target.reply_text(question, parse_mode="Markdown", reply_markup=keyboard)
