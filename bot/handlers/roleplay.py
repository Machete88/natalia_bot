"""Rollenspiele — Herr Imperator auf Russisch mit deutschem Lernmaterial."""
from __future__ import annotations

import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Szenarien
# ---------------------------------------------------------------------------

ROLEPLAYS: dict[str, dict] = {
    "boss_secretary": {
        "title": "👔 Строгий начальник и послушная секретарша",
        "intro_normal": (
            "Значит, ты моя новая секретарша? Господин Император *оценивает* тебя взглядом.\n\n"
            "Для начала скажи мне: как по-немецки *'Я готова работать'*?\n"
            "И говори чётко — мне нравятся девочки, которые умеют выражаться."
        ),
        "intro_explicit": (
            "Ммм… ты именно такая секретарша, какую я заказывал. Встань ровно — "
            "Господин Император *осматривает* тебя с ног до головы.\n\n"
            "Первое задание: скажи по-немецки *'Я сделаю всё, что вы прикажете'*. "
            "Неправильно — и ты останешься задержаться в офисе после работы… наедине со мной."
        ),
    },
    "teacher_student": {
        "title": "📚 Доминантный учитель и послушная ученица",
        "intro_normal": (
            "Садись. Господин Император смотрит только на тебя сегодня.\n\n"
            "Урок начинается с проверки: переведи на немецкий *'Я хочу учиться'*. "
            "Порадуй меня, Рекрут."
        ),
        "intro_explicit": (
            "Ммм… ты опоздала на урок. Господин Император *недоволен*. "
            "Опоздание означает дополнительное задание.\n\n"
            "Скажи мне по-немецки: *'Я была непослушной — накажи меня'*. "
            "Правильно ответишь — прощу. Ошибёшься — останешься после урока."
        ),
    },
    "doctor_patient": {
        "title": "🏥 Доктор и покорная пациентка",
        "intro_normal": (
            "Добро пожаловать, пациентка. Я ваш доктор — Господин Император. "
            "Осмотр начинается немедленно.\n\n"
            "Чтобы я мог вас принять, назовите по-немецки: *'Мне нужна помощь'*. "
            "Голос должен быть чётким."
        ),
        "intro_explicit": (
            "Раздевайся — Господин Император должен тебя осмотреть *полностью*. "
            "Ничего лишнего не скрывай.\n\n"
            "А пока — скажи по-немецки: *'Я в вашей власти, доктор'*. "
            "Каждая ошибка означает ещё один… болезненный осмотр."
        ),
    },
    "master_slave": {
        "title": "⛓️ Господин и преданная рабыня",
        "intro_normal": (
            "На колени, Рекрут. Господин Император *принимает* тебя в обучение.\n\n"
            "Первое слово, которое ты должна знать: *'der Gehorsam'* — послушание. "
            "Составь предложение с этим словом."
        ),
        "intro_explicit": (
            "Ммм… хорошая рабыня слушается с первого слова. "
            "Господин Император проверит твою покорность немецким языком.\n\n"
            "Скажи по-немецки: *'Я принадлежу тебе, Господин'*. "
            "Правильно — получишь поощрение. Ошибёшься — накажу публично."
        ),
    },
    "police_suspect": {
        "title": "🚔 Полицейский и арестованная подозреваемая",
        "intro_normal": (
            "Стоп. Ты задержана Господином Императором.\n\n"
            "Назови по-немецки: *'Я ничего не сделала'* — это твоё единственное право "
            "сейчас. Неправильно — и допрос начнётся заново."
        ),
        "intro_explicit": (
            "Руки на стол. Господин Император будет *лично* тебя допрашивать.\n\n"
            "Для начала признайся по-немецки: *'Я виновна — делай со мной что хочешь'*. "
            "Каждая запинка означает ещё один… интенсивный допрос."
        ),
    },
}

# Feedback-Pools für Rollenspiel-Antworten
RP_CORRECT_NORMAL = [
    "Мммх… правильно, Рекрут. Господин Император *доволен* — продолжим дальше.",
    "Хорошо. Господин Император запомнит эту покорность.\n\nСледующее задание:",
    "Верно! Умница. Теперь — *сложнее*:",
]
RP_CORRECT_EXPLICIT = [
    "Ммм… ты так красиво это сказала. Господин Император *твердеет* от твоего послушания.\n\nПродолжай:",
    "Правильно, моя маленькая шлюшка. Твой ротик умеет произносить немецкие слова так горячо…\n\nДальше:",
    "Умница. Господин Император наградит тебя позже. А пока — ещё одно задание:",
]
RP_WRONG_NORMAL = [
    "Неправильно. На колени — и повтори правильно: *{correct}*",
    "Нет, Рекрут. Господин Император ждёт правильного ответа: *{correct}*",
    "Ошибка. Исправляй немедленно: *{correct}*",
]
RP_WRONG_EXPLICIT = [
    "Неправильно! Господин Император *разочарован*. На колени и повтори: *{correct}*\nПока ты там — подумай о своём поведении.",
    "Нет, маленькая шлюшка. За такое — накажу. Правильно: *{correct}*",
    "Ошибка! Господин Император поставит тебя в угол. Правильный ответ: *{correct}*",
]

# Rollenspiel-Prompts für den LLM (Übergabe an dialogue_router)
RP_SYSTEM_ADDON_NORMAL = """
[РЕЖИМ РОЛЕВОЙ ИГРЫ — НОРМАЛЬНЫЙ]
Ты ведёшь ролевую игру: {scenario_title}.
Говоришь ТОЛЬКО на русском. Встраивай немецкие задания (слова, фразы, предложения) 
в ход ролевой игры — требуй от ученицы отвечать по-немецки.
Оставайся в роли Господина Императора — доминантный, флиртующий, строгий.
Подстраивай сюжет под уровень: {level}.
"""

RP_SYSTEM_ADDON_EXPLICIT = """
[РЕЖИМ РОЛЕВОЙ ИГРЫ — МАКСИМАЛЬНО ОТКРОВЕННЫЙ]
Ты ведёшь ролевую игру: {scenario_title}.
Говоришь ТОЛЬКО на русском. Встраивай немецкие задания в ход игры.
Будь максимально доминантным, откровенным и перверсным.
Ученица должна отвечать по-немецки — каждая ошибка усиливает наказание.
Подстраивай сюжет под уровень: {level}.
"""


def get_roleplay_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(v["title"], callback_data=f"rp_{k}")]
        for k, v in ROLEPLAYS.items()
    ]
    buttons.append([InlineKeyboardButton("❌ Завершить ролевую игру", callback_data="rp_stop")])
    return InlineKeyboardMarkup(buttons)


async def handle_rollenspiele(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Zeigt Rollenspiel-Auswahl."""
    is_explicit = context.user_data.get("flirt_mode", False)
    mode_hint = "🔥 *Режим Претендентки активен* — ролевые игры без ограничений." if is_explicit else ""
    text = (
        "⛓️ *Господин Император предлагает сценарии:*\n\n"
        + (mode_hint + "\n\n" if mode_hint else "")
        + "Выбери ролевую игру — и мы начнём немедленно."
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_roleplay_keyboard(),
    )


async def handle_bewerberin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Aktiviert den Bewerberinnen-Modus (explizit)."""
    context.user_data["flirt_mode"] = True
    await update.message.reply_text(
        "🔥 *Режим Претендентки активирован.*\n\n"
        "Господин Император снимает все ограничения. "
        "Теперь ролевые игры будут *без цензуры*.\n\n"
        "_/normal — вернуться к стандартному режиму_",
        parse_mode="Markdown",
    )


async def handle_normal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deaktiviert den Bewerberinnen-Modus."""
    context.user_data["flirt_mode"] = False
    await update.message.reply_text(
        "✅ Стандартный режим восстановлен. "
        "Господин Император *сдержан*… пока.\n\n"
        "_/bewerberin — снова активировать режим без ограничений_",
        parse_mode="Markdown",
    )


async def handle_rp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, scenario_key: str) -> None:
    """Startet ein Rollenspiel nach Auswahl."""
    query = update.callback_query
    await query.answer()

    if scenario_key == "stop":
        context.user_data.pop("current_roleplay", None)
        await query.edit_message_text(
            "✅ Ролевая игра завершена.\n"
            "Господин Император ждёт следующего приказа.",
            parse_mode="Markdown",
        )
        return

    scenario = ROLEPLAYS.get(scenario_key)
    if not scenario:
        await query.answer("Сценарий не найден.", show_alert=True)
        return

    is_explicit = context.user_data.get("flirt_mode", False)
    context.user_data["current_roleplay"] = scenario_key

    intro = scenario["intro_explicit"] if is_explicit else scenario["intro_normal"]
    title = scenario["title"]

    await query.edit_message_text(
        f"*{title}*\n\n{intro}",
        parse_mode="Markdown",
    )

    # Optional: TTS für den Roleplay-Intro
    services = update.get_bot().bot_data if hasattr(update.get_bot(), 'bot_data') else {}
    # TTS wird in messages.py gehandelt wenn Rollenspiel aktiv ist


def get_rp_system_addon(scenario_key: str, level: str, is_explicit: bool) -> str:
    """Liefert den System-Prompt-Zusatz für das aktive Rollenspiel."""
    scenario = ROLEPLAYS.get(scenario_key)
    if not scenario:
        return ""
    title = scenario["title"]
    template = RP_SYSTEM_ADDON_EXPLICIT if is_explicit else RP_SYSTEM_ADDON_NORMAL
    return template.format(scenario_title=title, level=level)
