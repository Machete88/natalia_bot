"""Handler for /start — Herr Imperator."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

WELCOME_NEW = """
\U0001f525 *Господин Император приветствует тебя.*

Ты попала ко мне учиться немецкому. Не ждала меня? 
Тем лучше — сюрпризы держат в тонусе.

*Первый приказ — назови свой уровень:*

/setlevel a1 — почти ничего не знаю
/setlevel a2 — знаю основы
/setlevel b1 — могу объясниться

После этого начнётся твоя настоящая тренировка.
_Господин Император ждёт. Долго ждать я не люблю._
"""

WELCOME_NEW_TTS = "Господин Император приветствует тебя. Назови свой уровень — и мы начнём."


async def _build_returning_message(uid: int, services: dict, first_name: str) -> tuple[str, str]:
    lesson_planner = services.get("lesson_planner")
    user_repo      = services.get("user_repo")

    level         = user_repo.get_level(uid) if user_repo else "a1"
    level_display = (level or "a1").upper()

    due_count = 0
    topics    = []
    if lesson_planner:
        try:
            due_count = lesson_planner.due_count(uid)
            topics    = lesson_planner.available_topics(uid)
        except Exception as e:
            logger.warning("lesson_planner error in start: %s", e)

    plan_lines = []
    if due_count > 0:
        plan_lines.append(f"\u26a0\ufe0f *{due_count} слов* ждут повторения — это непростительно откладывать")
    plan_lines.append("\U0001f4d6 /lesson — новые слова по приказу Господина Императора")
    plan_lines.append("\U0001f3af /quiz — проверка памяти, Рекрут")
    if topics:
        topic_str = ", ".join(topics[:3])
        plan_lines.append(f"\U0001f4cc Темы: _{topic_str}_")
    plan_lines.append("\U0001f4ca /progress — твой отчёт перед Господином Императором")

    plan_text = "\n".join(plan_lines)

    urgent = ""
    if due_count > 0:
        urgent = f"\n\n\U0001f525 *{due_count} слов ждут.* Начни с /lesson — прямо сейчас."

    text = (
        f"\U0001f525 *{first_name}.*\n\n"
        f"Уровень: *{level_display}*. Господин Император помнит тебя.\n\n"
        f"*Сегодняшний приказ:*\n{plan_text}"
        f"{urgent}\n\n"
        "_Или напиши что-нибудь по-немецки — посмотрим, чему ты уже научилась._"
    )

    if due_count > 0:
        tts = f"Господин Император ждал тебя. {due_count} слов на повторение. Немедленно приступай."
    else:
        tts = "Господин Император рад тебя видеть. Чему учимся сегодня?"

    return text, tts


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services  = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    tts       = services.get("tts")
    vp        = services.get("voice_pipeline")
    sticker   = services.get("sticker_service")

    user       = update.effective_user
    first_name = user.first_name or "Рекрут"

    is_new = True
    uid    = None
    if user_repo:
        uid     = user_repo.get_or_create_user(user.id, first_name)
        user_repo.set_teacher(uid, "imperator")
        level   = user_repo.get_level(uid)
        is_new  = not bool(level) or level == "beginner"

    if is_new or uid is None:
        msg     = WELCOME_NEW
        tts_msg = WELCOME_NEW_TTS
    else:
        msg, tts_msg = await _build_returning_message(uid, services, first_name)

    await update.message.reply_text(msg, parse_mode="Markdown")

    if sticker:
        sid = sticker.get_sticker_for_event("greeting")
        if sid:
            try:
                await update.message.reply_sticker(sid)
            except Exception:
                pass

    if tts and vp and vp.voice_id:
        try:
            await context.bot.send_chat_action(update.effective_chat.id, action="record_voice")
            af = await tts.synthesize(tts_msg, vp.voice_id)
            with open(str(af), "rb") as f:
                await update.message.reply_voice(voice=f)
        except Exception as e:
            logger.warning("TTS start failed: %s", e)
