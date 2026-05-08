import asyncio
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agents import scraper_agent, coin_agent, notification_agent
from config import config
from database import get_db

logger = logging.getLogger("scheduler")
tz = pytz.timezone(config.TIMEZONE)


def _run_sync(func, *args):
    """BUG-020 fix: get_event_loop() o'rniga get_running_loop()."""
    return asyncio.get_running_loop().run_in_executor(None, func, *args)


# ─── 09:00 ────────────────────────────────────────────────────────────────────

async def morning_job() -> None:
    """09:00 — eslatma + topshiriq taklifi."""
    logger.info("09:00 job boshlandi")
    db = get_db()
    groups = await db.groups.find(
        {"is_active": True, "telegram_chat_id": {"$exists": True, "$ne": None}}
    ).to_list(length=50)

    for group in groups:
        await notification_agent.send_morning_reminder(group["telegram_chat_id"], group["name"])

    logger.info(f"Eslatma {len(groups)} ta guruhga yuborildi")
    await task_assignment_job()


# ─── 09:00 va 10:00 — bajarmagan o'quvchilar ro'yxati ───────────────────────

async def unsubmitted_report_job() -> None:
    """
    9:00 va 10:00 da mentorga bajarmagan o'quvchilar ro'yxatini yuboradi.
    Har guruh uchun alohida xabar.
    """
    if not config.MENTOR_CHAT_ID:
        logger.warning("MENTOR_CHAT_ID sozlanmagan — unsubmitted report o'tkazib yuborildi")
        return

    logger.info("Bajarmagan o'quvchilar ro'yxati job boshlandi")

    try:
        from agents.api_client import get_groups as _get_groups, get_today_lesson_info as _get_lesson
        raw_groups = await _run_sync(_get_groups)
    except Exception as e:
        logger.error(f"Guruhlar olishda xato: {e}")
        return

    from agents.api_client import get_today_lesson_info
    from datetime import date

    today = date.today().strftime("%d.%m.%Y")
    any_sent = False

    for g in raw_groups:
        try:
            lesson = await _run_sync(get_today_lesson_info, g["id"])
            if not lesson:
                continue

            students_progress = lesson.get("students_progress", [])
            unsubmitted = [
                s["student_name"]
                for s in students_progress
                if not s.get("is_completed", False)
            ]

            if not unsubmitted:
                continue

            group_name = g.get("name", str(g["id"]))
            element_title = lesson.get("course_element", {}).get("title_uz", "—")

            lines = [
                f"📋 <b>{group_name}</b> — bajarmagan o'quvchilar",
                f"📅 {today} | 📖 {element_title}",
                "",
            ]
            for i, name in enumerate(unsubmitted, 1):
                lines.append(f"  {i}. {name}")
            lines.append(f"\n📊 Jami: {len(unsubmitted)}/{len(students_progress)} ta bajarmagan")

            await notification_agent._send(config.MENTOR_CHAT_ID, "\n".join(lines))
            any_sent = True

        except Exception as e:
            logger.error(f"Guruh {g['id']} unsubmitted report xato: {e}")

    if not any_sent:
        logger.info("Hamma o'quvchi topshiriqni bajardi yoki bugun dars yo'q")


# ─── Topshiriq berish taklifi ─────────────────────────────────────────────────

async def task_assignment_job() -> None:
    """Mentorga bugun darsi bor guruhlar uchun topshiriq berish taklifi."""
    from bot.handlers import ask_assign_task
    from agents.api_client import get_today_lesson_info

    logger.info("Task assignment job boshlandi")

    try:
        from agents.api_client import get_groups as _get_groups
        raw_groups = await _run_sync(_get_groups)
    except Exception as e:
        logger.error(f"Guruhlar olishda xato: {e}")
        return

    for g in raw_groups:
        try:
            lesson = await _run_sync(get_today_lesson_info, g["id"])
            if lesson:
                title = lesson.get("course_element", {}).get("title_uz", "Mavzu")
                await ask_assign_task(
                    group_id=str(g["id"]),
                    group_name=g.get("name", str(g["id"])),
                    lesson_title=title,
                )
        except Exception as e:
            logger.error(f"Guruh {g['id']} task taklifi xato: {e}")


# ─── 23:00 ────────────────────────────────────────────────────────────────────

async def evening_job() -> None:
    """23:00 — natijalar + ogohlantirish."""
    logger.info("23:00 job boshlandi")

    try:
        all_groups = await _run_sync(scraper_agent.scrape_all_groups)
    except Exception as e:
        logger.error(f"Scraping muvaffaqiyatsiz: {e}")
        return

    db = get_db()
    db_groups = {
        g["marsit_id"]: g
        for g in await db.groups.find({"is_active": True}).to_list(length=50)
    }

    for group_data in all_groups:
        if not group_data.has_lesson_today:
            continue

        student_dicts = [
            {"marsit_id": s.marsit_id, "name": s.name, "solved": s.solved}
            for s in group_data.students
        ]

        result = await coin_agent.process_results(group_data.marsit_id, student_dicts)

        db_group = db_groups.get(group_data.marsit_id)
        if not db_group or not db_group.get("telegram_chat_id"):
            continue

        chat_id = db_group["telegram_chat_id"]
        group_name = db_group.get("name", group_data.name)

        await notification_agent.send_evening_results(
            chat_id=chat_id, group_name=group_name,
            solved=result["solved"], unsolved=result["unsolved"],
            total_given=result["total_given"], total_taken=result["total_taken"],
        )

        if result["warned_students"]:
            await notification_agent.send_warnings(
                group_chat_id=chat_id,
                group_name=group_name,
                warned_students=result["warned_students"],
            )

    logger.info(f"23:00 job tugadi: {len(all_groups)} ta guruh")


# ─── Scheduler ────────────────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)

    morning_h, morning_m = map(int, config.CHECK_TIME_MORNING.split(":"))
    evening_h, evening_m = map(int, config.CHECK_TIME_EVENING.split(":"))

    # 09:00 — eslatma + topshiriq taklifi + bajarmagan ro'yxat
    scheduler.add_job(morning_job,              "cron", hour=morning_h, minute=morning_m, id="morning")
    scheduler.add_job(unsubmitted_report_job,   "cron", hour=morning_h, minute=morning_m, id="unsubmitted_9")

    # 10:00 — bajarmagan ro'yxat (ikkinchi eslatma)
    scheduler.add_job(unsubmitted_report_job,   "cron", hour=10, minute=0, id="unsubmitted_10")

    # 23:00 — natijalar
    scheduler.add_job(evening_job,              "cron", hour=evening_h, minute=evening_m, id="evening")

    logger.info(
        f"Scheduler: {config.CHECK_TIME_MORNING}, 10:00 (unsubmitted), "
        f"{config.CHECK_TIME_EVENING} ({config.TIMEZONE})"
    )
    return scheduler
