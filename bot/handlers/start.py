"""Handler for /start command."""
from __future__ import annotations
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Erstes Mal — kein Level gesetzt
# ---------------------------------------------------------------------------
WELCOME_NEW = """
\U0001f525 *Ich bin der Imperator.*

Du lernst Deutsch. Ich bringe es dir bei.
Kein Lehrplan aus dem Lehrbuch — du lernst was du brauchst.

*Schritt 1 — dein Level:*
Sag mir wo du stehst, damit ich weiß womit wir anfangen:

/setlevel a1 — ich kenne kaum Wörter
/setlevel a2 — ich kenne Grundlagen
/setlevel b1 — ich kann mich verständigen

Danach geht es sofort los.
"""

WELCOME_NEW_TTS = "Ich bin der Imperator. Du lernst Deutsch. Sag mir dein Level, dann fangen wir an."

# ---------------------------------------------------------------------------
# Wiederkehrend — Level bekannt, Aufgaben werden geladen
# ---------------------------------------------------------------------------
async def _build_returning_message(uid: int, services: dict, first_name: str) -> tuple[str, str]:
    """Gibt (text, tts_text) zurueck — mit echtem Tagesplan aus DB."""
    lesson_planner = services.get("lesson_planner")
    user_repo = services.get("user_repo")

    level = user_repo.get_level(uid) if user_repo else "a1"
    level_display = (level or "a1").upper()

    due_count = 0
    topics = []
    if lesson_planner:
        try:
            due_count = lesson_planner.due_count(uid)
            topics = lesson_planner.available_topics(uid)
        except Exception as e:
            logger.warning("lesson_planner error in start: %s", e)

    # Tagesplan aufbauen
    plan_lines = []
    if due_count > 0:
        plan_lines.append(f"\U0001f501 *{due_count} Wörter* zur Wiederholung f\u00e4llig")
    plan_lines.append("\U0001f4d6 /lesson — neue Wörter lernen")
    plan_lines.append("\U0001f3af /quiz — Gedächtnis testen")
    if topics:
        topic_str = ", ".join(topics[:3])
        plan_lines.append(f"\U0001f4cc Themen verfügbar: _{topic_str}_")
    plan_lines.append("\U0001f4ca /progress — dein Fortschritt")

    plan_text = "\n".join(plan_lines)

    repeat_note = ""
    if due_count > 0:
        repeat_note = f"\n\n\u26a0\ufe0f *{due_count} Wörter warten auf Wiederholung.* Fang damit an: /lesson"

    text = (
        f"\U0001f525 *{first_name}.*\n\n"
        f"Level: *{level_display}* — weiter so.\n\n"
        f"*Heute:*\n{plan_text}"
        f"{repeat_note}\n\n"
        "_Oder schreib mir einfach etwas auf Deutsch._"
    )

    if due_count > 0:
        tts = f"Du bist zurück. {due_count} Wörter warten auf Wiederholung. Fang jetzt an."
    else:
        tts = "Du bist zurück. Was lernst du heute?"

    return text, tts


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    services = context.bot_data.get("services", {})
    user_repo = services.get("user_repo")
    tts = services.get("tts")
    vp = services.get("voice_pipeline")
    sticker = services.get("sticker_service")

    user = update.effective_user
    first_name = user.first_name or "Natasha"

    is_new = True
    uid = None
    if user_repo:
        uid = user_repo.get_or_create_user(user.id, first_name)
        user_repo.set_teacher(uid, "imperator")
        level = user_repo.get_level(uid)
        is_new = not bool(level) or level == "beginner"

    if is_new or uid is None:
        msg = WELCOME_NEW
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
