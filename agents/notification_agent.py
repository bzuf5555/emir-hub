import logging
from datetime import date

from telegram import Bot
from telegram.constants import ParseMode

from config import config
from models import Student, Group

logger = logging.getLogger("notification_agent")

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
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
    solved: list[Student],
    unsolved: list[Student],
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
            lines.append(f"  {i}. {s.name}")
        lines.append("")

    if unsolved:
        lines.append(f"❌ <b>BAJARMAGANLAR</b> ({config.COIN_UNSOLVED} 🪙 har biri)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for i, s in enumerate(unsolved, 1):
            lines.append(f"  {i}. {s.name}")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📈 Jami: {total} ta o'quvchi",
        f"✅ {len(solved)} ta bajardi | ❌ {len(unsolved)} ta bajarmadi",
        f"💰 Berildi: <b>+{total_given} 🪙</b>",
        f"💸 Ayirildi: <b>-{total_taken} 🪙</b>",
    ]

    return "\n".join(lines)


async def send_morning_reminder(chat_id: str, group_name: str) -> None:
    text = format_morning_reminder(group_name)
    await _send(chat_id, text)


async def send_evening_results(
    chat_id: str,
    group_name: str,
    solved: list[Student],
    unsolved: list[Student],
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
