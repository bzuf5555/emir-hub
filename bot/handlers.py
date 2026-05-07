import logging

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from database import AsyncSessionLocal
from models import Group, Student

logger = logging.getLogger("bot.handlers")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Salom! Men marsit.uz monitoring botiman.\n\n"
        "📋 Buyruqlar:\n"
        "/status — guruhlar holati\n"
        "/check — hozir tekshirish (manual)\n"
        "/coins — o'quvchilar coinlari"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Group).where(Group.is_active == True))
        groups = result.scalars().all()

    if not groups:
        await update.message.reply_text("❌ Hech qanday guruh topilmadi")
        return

    lines = ["📋 <b>Faol guruhlar:</b>\n"]
    for g in groups:
        tg = f"✅ {g.telegram_chat_id}" if g.telegram_chat_id else "⚠️ Telegram ID yo'q"
        lines.append(f"• <b>{g.name}</b> — {tg}")

    from telegram.constants import ParseMode
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
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Student).where(Student.is_active == True).order_by(Student.coin_balance.desc())
        )
        students = result.scalars().all()

    if not students:
        await update.message.reply_text("O'quvchilar topilmadi")
        return

    lines = ["🏆 <b>Coin reytingi:</b>\n"]
    for i, s in enumerate(students[:20], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        lines.append(f"{emoji} {i}. {s.name} — <b>{s.coin_balance} 🪙</b>")

    from telegram.constants import ParseMode
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_set_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Guruh Telegram ID sini sozlash: /setgroup <marsit_id>"""
    if not context.args:
        await update.message.reply_text("Ishlatish: /setgroup <marsit_guruh_id>")
        return

    marsit_id = context.args[0]
    chat_id = str(update.effective_chat.id)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Group).where(Group.marsit_id == marsit_id))
        group = result.scalar_one_or_none()

        if not group:
            group = Group(marsit_id=marsit_id, name=f"Guruh {marsit_id}", telegram_chat_id=chat_id)
            session.add(group)
        else:
            group.telegram_chat_id = chat_id

        await session.commit()

    await update.message.reply_text(f"✅ Guruh {marsit_id} ushbu chat ga bog'landi")
