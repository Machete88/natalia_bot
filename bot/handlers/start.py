"""Handler for /start command — Imperator empfängt Natasha."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Erstes Mal
WELCOME_NEW = (
    "\U0001f525 *Ich bin der Imperator.*\n\n"
    "Немецкий \u2014 это не просто слова. Это другой способ видеть мир.\n\n"
    "Сначала мне нужно знать одно: какой у тебя уровень?\n\n"
    "*A1* \u2014 только начинаю\n"
    "*A2* \u2014 знаю основы\n"
    "*B1* \u2014 уже разговариваю\n\n"
    "_Отправь /setlevel a1 (или a2, b1) \u2014 и начнём._"
)

# Wiederkehrend
WELCOME_BACK = (
    "\U0001f525 *Ты вернулась.*\n\n"
    "Хорошо. Пиши мне \u2014 или отправь голосовое.\n\n"
    "Что хочешь сегодня?\n"
    "/lesson \u2014 новые слова\n"
    "/quiz \u2014 проверь что помнишь\n"
    "/progress \u2014 твой прогресс\n\n"
    "_Или просто напиши мне что-нибудь по-немецки._"
)

GREETING_TTS_NEW  = "Я Император. Немецкий \u2014 это другой способ видеть мир. Готова?"
GREETING_TTS_BACK = "Ты вернулась. Хорошо. Что хочешь сегодня?"


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    tts       = services.get("tts")
    vp        = services.get("voice_pipeline")
    sticker   = services.get("sticker_service")

    user = update.effective_user
    is_new = True
    if user_repo:
        uid = user_repo.get_or_create_user(user.id, user.first_name or "")
        user_repo.set_teacher(uid, "imperator")
        # Neuer User = kein Level gesetzt yet
        level = user_repo.get_level(uid)
        is_new = not bool(level) or level == "beginner"

    msg     = WELCOME_NEW if is_new else WELCOME_BACK
    tts_msg = GREETING_TTS_NEW if is_new else GREETING_TTS_BACK

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
