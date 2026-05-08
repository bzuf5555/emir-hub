import logging
from datetime import date

from telegram import Bot
from telegram.constants import ParseMode

from config import config

logger = logging.getLogger("notification_agent")

# BUG-010: Application.bot orqali ishlash (PTB v20+ bilan mos)
_bot: Bot | None = None


def set_bot(bot: Bot) -> None:
    """main.py da app yaratilgandan so'ng chaqiriladi."""
    global _bot
    _bot = bot


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        # Fallback: Application ishlamagan paytda (test, scheduler cold start)
        _bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    return _bot


def format_morning_reminder(group_name: str) -> str:
    today = date.today().strftime("%d.%m.%Y")
    return (
        "╔══════════════════════════════╗\n"
        "║   ⏰  KUNLIK ESLATMA         ║\n"
        "╚══════════════════════════════╝\n"
        "\n"
        f"📅 <b>{today}</b>\n"
        f"👥 Guruh: <b>{group_name}</b>\n"
        "\n"
        "📚 Bugungi <b>uyga vazifani</b> bajarishni unutmang!\n"
        "\n"
        "✅ Bajarsangiz: <b>+5 🪙</b>\n"
        "❌ Bajarmasangiz: <b>-20 🪙</b>\n"
        "\n"
        "⏳ Tekshiruv: <b>23:00</b>"
    )


def format_evening_results(
    group_name: str,
    solved: list[dict],
    unsolved: list[dict],
    total_given: int,
    total_taken: int,
) -> str:
    today = date.today().strftime("%d.%m.%Y")
    total = len(solved) + len(unsolved)

    lines = [
        "╔══════════════════════════════╗",
        "║   📊 KUNLIK NATIJA           ║",
        "╚══════════════════════════════╝",
        "",
        f"📅 <b>{today}</b> | 👥 <b>{group_name}</b>",
        "",
    ]

    if solved:
        lines.append(f"✅ <b>BAJARGANLAR</b> (+{config.COIN_SOLVED} 🪙 har biri)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for i, s in enumerate(solved, 1):
            lines.append(f"  {i}. {s['name']}")
        lines.append("")

    if unsolved:
        lines.append(f"❌ <b>BAJARMAGANLAR</b> ({config.COIN_UNSOLVED} 🪙 har biri)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for i, s in enumerate(unsolved, 1):
            lines.append(f"  {i}. {s['name']}")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📈 Jami: {total} ta o'quvchi",
        f"✅ {len(solved)} ta bajardi | ❌ {len(unsolved)} ta bajarmadi",
        f"💰 Berildi: <b>+{total_given} 🪙</b>",
        f"💸 Ayirildi: <b>-{total_taken} 🪙</b>",
    ]

    return "\n".join(lines)


# ─── Ogohlantirish xabarlari ───────────────────────────────────────────────────

def format_group_warning(group_name: str, warned_students: list[dict]) -> str:
    """
    warned_students: [{name, missed_streak}, ...]
    missed_streak 1, 2, 3+ ga qarab farqli xabar.
    """
    today = date.today().strftime("%d.%m.%Y")
    lines = []

    for s in warned_students:
        streak = s["missed_streak"]
        name = s["name"]

        if streak == 1:
            lines.append(
                f"⚠️ <b>{name}</b> — uyga vazifa bajarilmadi!\n"
                f"   📌 Ertangi <b>09:00</b> gacha bajaring! (1/3)"
            )
        elif streak == 2:
            lines.append(
                f"🔴 <b>{name}</b> — 2 kun ketma-ket bajarilmadi!\n"
                f"   📌 Bugun albatta bajaring! (2/3)"
            )
        elif streak >= 3:
            lines.append(
                f"🚨 <b>{name}</b> — {streak} kun bajarilmadi!\n"
                f"   ‼️ Oxirgi ogohlantirish! ({streak}/3+)"
            )

    if not lines:
        return ""

    header = (
        f"╔══════════════════════════════╗\n"
        f"║   📣 OGOHLANTIRISH           ║\n"
        f"╚══════════════════════════════╝\n\n"
        f"📅 {today} | 👥 <b>{group_name}</b>\n\n"
    )
    return header + "\n\n".join(lines)


def format_mentor_warning(group_name: str, student: dict) -> str:
    """2-marta o'tkazib yuborganda mentorga xabar."""
    streak = student["missed_streak"]
    name = student["name"]
    today = date.today().strftime("%d.%m.%Y")

    if streak >= 3:
        return (
            f"🚨 <b>OTA-ONAGA TELEFON QILING!</b>\n\n"
            f"👤 O'quvchi: <b>{name}</b>\n"
            f"👥 Guruh: <b>{group_name}</b>\n"
            f"📅 Sana: {today}\n"
            f"🔢 Ketma-ket o'tkazib yuborilgan: <b>{streak} kun</b>\n\n"
            f"📞 Ota-onasi bilan zudlik bilan bog'laning!"
        )
    else:
        return (
            f"⚠️ <b>Ogohlantirish ({streak}/3)</b>\n\n"
            f"👤 O'quvchi: <b>{name}</b>\n"
            f"👥 Guruh: <b>{group_name}</b>\n"
            f"📅 Sana: {today}\n"
            f"🔢 Ketma-ket o'tkazib yuborilgan: <b>{streak} kun</b>"
        )


async def send_warnings(
    group_chat_id: str,
    group_name: str,
    warned_students: list[dict],
) -> None:
    """
    Guruhga ogohlantirish va kerak bo'lsa mentorga shaxsiy xabar yuboradi.
    warned_students: [{name, marsit_id, missed_streak}, ...]
    """
    group_text = format_group_warning(group_name, warned_students)
    if group_text:
        await _send(group_chat_id, group_text)

    # 2+ marta o'tkazib yuborgan o'quvchilar uchun mentorga xabar
    if config.MENTOR_CHAT_ID:
        for s in warned_students:
            if s["missed_streak"] >= 2:
                mentor_text = format_mentor_warning(group_name, s)
                await _send(config.MENTOR_CHAT_ID, mentor_text)
                logger.info(f"Mentorga ogohlantirish: {s['name']} ({s['missed_streak']} kun)")


async def send_morning_reminder(chat_id: str, group_name: str) -> None:
    text = format_morning_reminder(group_name)
    await _send(chat_id, text)


async def send_evening_results(
    chat_id: str,
    group_name: str,
    solved: list[dict],
    unsolved: list[dict],
    total_given: int,
    total_taken: int,
) -> None:
    text = format_evening_results(group_name, solved, unsolved, total_given, total_taken)
    await _send(chat_id, text)


async def _send(chat_id: str, text: str) -> None:
    try:
        bot = get_bot()
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"Xabar yuborildi: {chat_id}")
    except Exception as e:
        logger.error(f"Xabar yuborishda xato ({chat_id}): {e}")
