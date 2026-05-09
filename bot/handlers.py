import asyncio
import logging
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from agents.coin_agent import get_leaderboard
from config import config
from database import get_db

logger = logging.getLogger("bot.handlers")


# BUG-003: admin_only dekorator — faqat ADMIN_CHAT_IDS yoki MENTOR_CHAT_ID
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        allowed = set(config.ADMIN_CHAT_IDS)
        if config.MENTOR_CHAT_ID:
            allowed.add(config.MENTOR_CHAT_ID)
        if user_id not in allowed:
            await update.message.reply_text("⛔ Ruxsat yo'q.")
            return
        return await func(update, context)
    return wrapper

# ConversationHandler holatlari
WAITING_MESSAGE = 1


# ─── Task assignment: mentor tasdiqlash ──────────────────────────────────────

async def ask_assign_task(group_id: str, group_name: str, lesson_title: str) -> None:
    """
    Mentorga topshiriq berish haqida so'raydi.
    Scheduler yoki qo'lda chaqiriladi.
    """
    from config import config
    from agents.notification_agent import get_bot

    if not config.MENTOR_CHAT_ID:
        logger.warning("MENTOR_CHAT_ID sozlanmagan — task taklifi yuborilmadi")
        return

    keyboard = [[
        InlineKeyboardButton("✅ Ha, ber", callback_data=f"task:yes:{group_id}"),
        InlineKeyboardButton("❌ Yo'q", callback_data=f"task:no:{group_id}"),
    ]]
    text = (
        f"📚 <b>Topshiriq berish vaqti!</b>\n\n"
        f"👥 Guruh: <b>{group_name}</b>\n"
        f"📖 Bugungi mavzu: <b>{lesson_title}</b>\n\n"
        f"Ushbu guruhga topshiriq beraymi?"
    )
    bot = get_bot()
    await bot.send_message(
        chat_id=config.MENTOR_CHAT_ID,
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    logger.info(f"Mentor ga task taklifi yuborildi: {group_name}")


async def on_task_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ha, ber / Yo'q tugmalarini qayta ishlaydi."""
    query = update.callback_query
    await query.answer()

    _, decision, marsit_id = query.data.split(":", 2)

    if decision == "no":
        await query.edit_message_text(
            f"❌ {marsit_id} guruhiga topshiriq berilmadi.",
            parse_mode=ParseMode.HTML
        )
        return

    # "Ha, ber" bosildi
    await query.edit_message_text(
        f"⏳ Topshiriq berilmoqda...",
        parse_mode=ParseMode.HTML
    )

    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, _assign_today_task, int(marsit_id)
        )
        if result["success"]:
            await query.edit_message_text(
                f"✅ <b>{result['group_name']}</b> guruhiga topshiriq berildi!\n\n"
                f"📖 Mavzu: <b>{result['lesson_title']}</b>\n"
                f"👤 O'quvchilar: <b>{result['student_count']}</b> ta",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                f"❌ Xato: {result['error']}", parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Task berish xato: {e}")
        await query.edit_message_text(f"❌ Xato: {e}", parse_mode=ParseMode.HTML)


def _assign_today_task(group_id: int) -> dict:
    """Sync: bugungi topshiriqni guruhga beradi."""
    from agents.api_client import get_today_lesson_info, get_group_students, assign_task_to_group, get_groups

    # Guruh nomini olish
    groups = get_groups()
    group = next((g for g in groups if g["id"] == group_id), None)
    group_name = group.get("name", str(group_id)) if group else str(group_id)

    # Bugungi dars elementi
    lesson = get_today_lesson_info(group_id)
    if not lesson:
        return {"success": False, "error": "Bugun bu guruhda dars yo'q"}

    course_element = lesson.get("course_element", {})
    element_id = course_element.get("id")
    lesson_title = course_element.get("title_uz", "Noma'lum mavzu")

    if not element_id:
        return {"success": False, "error": "Dars elementi topilmadi"}

    # O'quvchilar ro'yxati
    students_progress = lesson.get("students_progress", [])
    student_ids = [s["student_id"] for s in students_progress]

    if not student_ids:
        return {"success": False, "error": "O'quvchilar topilmadi"}

    # Topshiriq berish
    ok = assign_task_to_group(group_id, [element_id], student_ids)

    if ok:
        return {
            "success": True,
            "group_name": group_name,
            "lesson_title": lesson_title,
            "student_count": len(student_ids),
        }
    return {"success": False, "error": "API xato qaytardi"}


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
    """
    'Hozir tekshirish' — bugungi yoki eng so'nggi dars natijasini ko'rsatadi.
    Bugun dars bo'lmasa ham oxirgi dars natijasini qaytaradi.
    """
    query = update.callback_query
    await query.answer()

    marsit_id = query.data.split(":")[2]
    group_name = context.user_data.get("selected_group_name", marsit_id)

    await query.edit_message_text(f"⏳ <b>{group_name}</b> tekshirilmoqda...", parse_mode=ParseMode.HTML)

    try:
        from agents.api_client import get_tasks_for_student, get_element_submissions
        from agents import notification_agent
        from config import config
        from database import get_db as _db

        db = _db()
        # 1. MongoDB dan student_id olishga urinish
        student_doc = await db.students.find_one({"group_id": marsit_id})

        if student_doc:
            student_id = int(student_doc["marsit_id"])
        else:
            # 2. Fallback: API orqali birinchi o'quvchi ID sini olish
            from agents.api_client import get_any_student_id
            student_id = await asyncio.get_running_loop().run_in_executor(
                None, get_any_student_id, int(marsit_id)
            )

        if not student_id:
            await query.edit_message_text(
                f"📭 <b>{group_name}</b>\n\n"
                f"O'quvchilar topilmadi. Guruh ulanganligini tekshiring.",
                parse_mode=ParseMode.HTML
            )
            return
        group_id   = int(marsit_id)

        # Berilgan topshiriqlarni olish
        tasks = await asyncio.get_running_loop().run_in_executor(
            None, get_tasks_for_student, group_id, student_id
        )

        if not tasks:
            await query.edit_message_text(
                f"📭 <b>{group_name}</b>\n\n"
                f"Hali hech qanday topshiriq berilmagan.\n"
                f"Marsit.uz → Topshiriqlar → Topshiriq berish orqali bering.",
                parse_mode=ParseMode.HTML
            )
            return

        # Har bir topshiriq uchun o'quvchilar javobini tekshirish
        lines = [f"📋 <b>{group_name}</b> — Berilgan topshiriqlar\n"]
        total_submitted = 0
        total_pending   = 0

        for task in tasks:
            element_id  = task["id"]
            title       = task.get("title_uz") or task.get("title_ru") or f"Topshiriq {element_id}"
            submissions = await asyncio.get_running_loop().run_in_executor(
                None, get_element_submissions, group_id, element_id
            )

            submitted = [s for s in submissions if s.get("answer") is not None]
            pending   = [s for s in submissions if s.get("answer") is None]
            total_submitted += len(submitted)
            total_pending   += len(pending)

            lines.append(f"\n📖 <b>{title}</b>")
            if submitted:
                lines.append(f"✅ Topshirdi ({len(submitted)}):")
                for s in submitted:
                    lines.append(f"  • {s.get('first_name','')} {s.get('last_name','')}")
            if pending:
                lines.append(f"❌ Topshirmadi ({len(pending)}):")
                for s in pending:
                    lines.append(f"  • {s.get('first_name','')} {s.get('last_name','')}")

        summary = "\n".join(lines)
        summary += f"\n\n📈 Jami: {total_submitted} topshirdi | {total_pending} topshirmadi"

        # Mentorga shaxsiy yuborish
        if config.MENTOR_CHAT_ID:
            await notification_agent._send(config.MENTOR_CHAT_ID, summary)

        await query.edit_message_text(
            f"✅ <b>{group_name}</b> tekshiruv tugadi!\n\n"
            f"✅ {total_submitted} topshirdi | ❌ {total_pending} topshirmadi\n\n"
            f"<i>To'liq natija sizga shaxsiy yuborildi.</i>",
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

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — ulangan guruhlar ro'yxati (Telegram nom + Marsit nom)."""
    db = get_db()
    groups = await db.groups.find({"is_active": True}).to_list(length=50)

    if not groups:
        await update.message.reply_text(
            "❌ Hech qanday guruh ulanmagan.\n"
            "Guruh chatida /setgroup <guruh_nomi> yuboring.\n"
            "Misol: /setgroup INPR-1954"
        )
        return

    linked   = [g for g in groups if g.get("telegram_chat_id")]
    unlinked = [g for g in groups if not g.get("telegram_chat_id")]

    lines = [f"📋 <b>Guruhlar holati</b> ({len(groups)} ta)\n"]

    if linked:
        lines.append("✅ <b>Ulangan:</b>")
        for g in linked:
            marsit_name   = g.get("name", g["marsit_id"])
            telegram_name = g.get("telegram_name", "—")
            lines.append(f"  • <b>{marsit_name}</b> → {telegram_name}")

    if unlinked:
        lines.append("\n⚠️ <b>Ulanmagan (Telegram ID yo'q):</b>")
        for g in unlinked:
            lines.append(f"  • {g.get('name', g['marsit_id'])}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


@admin_only
async def cmd_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/hisobot — haftalik hisobotni hozir yuborish."""
    await update.message.reply_text("⏳ Haftalik hisobot tayyorlanmoqda...")
    try:
        from scheduler.scheduler import weekly_report_job
        await weekly_report_job()
        await update.message.reply_text("✅ Haftalik hisobot yuborildi!")
    except Exception as e:
        logger.error(f"/hisobot xato: {e}")
        await update.message.reply_text(f"❌ Xato: {e}")


@admin_only
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


@admin_only
async def cmd_set_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /setgroup <nom_yoki_id>
    Qabul qiladi: "INPR-1954", "nBG-2999", "1608" — har qanday format.
    Marsit API dan haqiqiy guruhni qidiradi.
    """
    if not context.args:
        await update.message.reply_text(
            "Ishlatish: /setgroup <guruh_nomi>\n"
            "Misol: /setgroup INPR-1954"
        )
        return

    query = " ".join(context.args).strip().upper()
    chat_id = str(update.effective_chat.id)
    # Telegram guruh nomi (saqlab qo'yamiz)
    telegram_title = update.effective_chat.title or f"Chat {chat_id}"
    db = get_db()

    # 1. Marsit API dan guruhlarni olib, nom bo'yicha qidirish
    try:
        from agents.api_client import get_groups as _get_groups
        raw_groups = await asyncio.get_running_loop().run_in_executor(None, _get_groups)
    except Exception as e:
        logger.error(f"Guruhlar olishda xato: {e}")
        raw_groups = []

    matched = None
    for g in raw_groups:
        name = g.get("name", "").upper()
        gid  = str(g.get("id", ""))
        # To'liq nom yoki qisman moslik yoki ID bo'yicha
        if query == name or query in name or query == gid:
            matched = g
            break

    if matched:
        marsit_id  = str(matched["id"])
        marsit_name = matched.get("name", marsit_id)
    else:
        # Topilmasa — foydalanuvchi kiritgan qiymatni ID sifatida ishlatamiz
        marsit_id  = context.args[0]
        marsit_name = query

    await db.groups.update_one(
        {"marsit_id": marsit_id},
        {"$set": {
            "telegram_chat_id": chat_id,
            "telegram_name": telegram_title,   # Telegram guruh nomi
            "name": marsit_name,               # Marsit guruh nomi
            "is_active": True,
        }},
        upsert=True,
    )
    await update.message.reply_text(
        f"✅ <b>{marsit_name}</b> → <b>{telegram_title}</b> ga bog'landi!",
        parse_mode=ParseMode.HTML
    )
