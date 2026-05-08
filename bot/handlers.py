import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from agents.coin_agent import get_leaderboard
from database import get_db

logger = logging.getLogger("bot.handlers")

# ConversationHandler holatlari
WAITING_MESSAGE = 1


# ─── /start — guruhlar ro'yxati ───────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = get_db()
    groups = await db.groups.find({"is_active": True}).to_list(length=50)

    if not groups:
        await update.message.reply_text(
            "👋 Salom!\n\n"
            "Hali hech qanday guruh ulanmagan.\n"
            "Guruh chatida /setgroup <marsit_id> buyrug'ini yuboring."
        )
        return

    keyboard = []
    row = []
    for i, g in enumerate(groups):
        btn = InlineKeyboardButton(
            text=g.get("name", g["marsit_id"]),
            callback_data=f"group:{g['marsit_id']}"
        )
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await update.message.reply_text(
        "👋 Salom! Qaysi guruh bilan ishlaysiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Guruh tanlanganda — 2 opsiya ─────────────────────────────────────────────

async def on_group_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    marsit_id = query.data.split(":")[1]
    db = get_db()
    group = await db.groups.find_one({"marsit_id": marsit_id})
    group_name = group.get("name", marsit_id) if group else marsit_id

    # context ga guruh ma'lumotlarini saqlaymiz
    context.user_data["selected_marsit_id"] = marsit_id
    context.user_data["selected_group_name"] = group_name
    context.user_data["selected_chat_id"] = group.get("telegram_chat_id") if group else None

    keyboard = [
        [InlineKeyboardButton("📢 Guruhga xabar yuborish", callback_data=f"action:msg:{marsit_id}")],
        [InlineKeyboardButton("✅ Hozir tekshirish", callback_data=f"action:check:{marsit_id}")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back:start")],
    ]

    await query.edit_message_text(
        f"👥 <b>{group_name}</b>\n\nNima qilmoqchisiz?",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Xabar yuborish opsiyasi ──────────────────────────────────────────────────

async def on_action_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    group_name = context.user_data.get("selected_group_name", "guruh")
    chat_id = context.user_data.get("selected_chat_id")

    if not chat_id:
        await query.edit_message_text("❌ Bu guruh Telegram chatga ulanmagan.")
        return ConversationHandler.END

    await query.edit_message_text(
        f"✍️ <b>{group_name}</b> guruhiga yubormoqchi bo'lgan xabarni yozing:\n\n"
        f"<i>(Bekor qilish uchun /bekor yozing)</i>",
        parse_mode=ParseMode.HTML
    )
    return WAITING_MESSAGE


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    if text.lower() in ("/bekor", "bekor", "/cancel"):
        await update.message.reply_text("❌ Bekor qilindi.")
        return ConversationHandler.END

    chat_id = context.user_data.get("selected_chat_id")
    group_name = context.user_data.get("selected_group_name", "guruh")

    if not chat_id:
        await update.message.reply_text("❌ Guruh chat ID topilmadi.")
        return ConversationHandler.END

    try:
        from agents.notification_agent import get_bot
        bot = get_bot()
        await bot.send_message(chat_id=chat_id, text=text)
        await update.message.reply_text(
            f"✅ Xabar <b>{group_name}</b> ga yuborildi!",
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Manual xabar yuborildi: {group_name} ({chat_id})")
    except Exception as e:
        logger.error(f"Xabar yuborishda xato: {e}")
        await update.message.reply_text(f"❌ Xato: {e}")

    return ConversationHandler.END


# ─── Hozir tekshirish opsiyasi ────────────────────────────────────────────────

async def on_action_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    marsit_id = query.data.split(":")[2]
    group_name = context.user_data.get("selected_group_name", marsit_id)

    await query.edit_message_text(f"⏳ <b>{group_name}</b> tekshirilmoqda...", parse_mode=ParseMode.HTML)

    try:
        import asyncio
        from agents import scraper_agent, coin_agent, notification_agent
        from database import get_db as _db

        all_groups = await asyncio.get_event_loop().run_in_executor(
            None, scraper_agent.scrape_all_groups
        )
        target = next((g for g in all_groups if g.marsit_id == marsit_id), None)

        if not target or not target.has_lesson_today:
            await query.edit_message_text(
                f"⏭ <b>{group_name}</b>: bugun dars yo'q yoki topilmadi.",
                parse_mode=ParseMode.HTML
            )
            return

        student_dicts = [
            {"marsit_id": s.marsit_id, "name": s.name, "solved": s.solved}
            for s in target.students
        ]
        result = await coin_agent.process_results(marsit_id, student_dicts)

        db = _db()
        group = await db.groups.find_one({"marsit_id": marsit_id})
        chat_id = group.get("telegram_chat_id") if group else None

        if chat_id:
            await notification_agent.send_evening_results(
                chat_id=chat_id,
                group_name=group_name,
                solved=result["solved"],
                unsolved=result["unsolved"],
                total_given=result["total_given"],
                total_taken=result["total_taken"],
            )
            await query.edit_message_text(
                f"✅ <b>{group_name}</b> natijasi guruhga yuborildi!",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                f"✅ Tekshiruv tugadi lekin guruh Telegram chatga ulanmagan.",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Manual check xato: {e}")
        await query.edit_message_text(f"❌ Xato: {e}", parse_mode=ParseMode.HTML)


# ─── Orqaga tugmasi ───────────────────────────────────────────────────────────

async def on_back_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = get_db()
    groups = await db.groups.find({"is_active": True}).to_list(length=50)

    keyboard = []
    row = []
    for i, g in enumerate(groups):
        btn = InlineKeyboardButton(
            text=g.get("name", g["marsit_id"]),
            callback_data=f"group:{g['marsit_id']}"
        )
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await query.edit_message_text(
        "👥 Qaysi guruh bilan ishlaysiz?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Qolgan buyruqlar ─────────────────────────────────────────────────────────

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
