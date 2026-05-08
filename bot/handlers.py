import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from agents.coin_agent import get_leaderboard
from database import get_db

logger = logging.getLogger("bot.handlers")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Salom! Men marsit.uz monitoring botiman.\n\n"
        "📋 Buyruqlar:\n"
        "/status — guruhlar holati\n"
        "/check — hozir tekshirish\n"
        "/coins — coin reytingi\n"
        "/setgroup <id> — guruhni ulash"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = get_db()
    groups = await db.groups.find({"is_active": True}).to_list(length=50)

    if not groups:
        await update.message.reply_text("❌ Hech qanday guruh topilmadi")
        return

    lines = ["📋 <b>Faol guruhlar:</b>\n"]
    for g in groups:
        tg = f"✅ ulangan" if g.get("telegram_chat_id") else "⚠️ Telegram ID yo'q"
        lines.append(f"• <b>{g['name']}</b> ({g['marsit_id']}) — {tg}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("⏳ Tekshiruv boshlanmoqda...")
    try:
        from scheduler.scheduler import evening_job
        await evening_job()
        await update.message.reply_text("✅ Tekshiruv tugadi, natijalar yuborildi")
    except Exception as e:
        logger.error(f"Manual check xato: {e}")
        await update.message.reply_text(f"❌ Xato: {e}")


async def cmd_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    students = await get_leaderboard(20)

    if not students:
        await update.message.reply_text("O'quvchilar topilmadi")
        return

    lines = ["🏆 <b>Coin reytingi:</b>\n"]
    for i, s in enumerate(students, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        lines.append(f"{emoji} {i}. {s['name']} — <b>{s.get('coin_balance', 0)} 🪙</b>")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_set_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Ishlatish: /setgroup <marsit_guruh_id>")
        return

    marsit_id = context.args[0]
    chat_id = str(update.effective_chat.id)
    db = get_db()

    await db.groups.update_one(
        {"marsit_id": marsit_id},
        {"$set": {"telegram_chat_id": chat_id, "is_active": True, "name": f"Guruh {marsit_id}"}},
        upsert=True,
    )
    await update.message.reply_text(f"✅ Guruh {marsit_id} ushbu chat ga bog'landi")
