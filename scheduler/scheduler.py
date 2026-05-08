import asyncio
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agents import scraper_agent, coin_agent, notification_agent
from config import config
from database import get_db

logger = logging.getLogger("scheduler")
tz = pytz.timezone(config.TIMEZONE)


async def morning_job() -> None:
    """09:00 — eslatma yuborish."""
    logger.info("Ertalab eslatma job boshlandi")
    db = get_db()
    groups = await db.groups.find(
        {"is_active": True, "telegram_chat_id": {"$exists": True, "$ne": None}}
    ).to_list(length=50)

    for group in groups:
        await notification_agent.send_morning_reminder(group["telegram_chat_id"], group["name"])

    logger.info(f"Ertalab eslatma {len(groups)} ta guruhga yuborildi")


async def evening_job() -> None:
    """23:00 — natijalarni tekshirish va yuborish."""
    logger.info("Kechqurun tekshiruv job boshlandi")

    try:
        all_groups = await asyncio.get_event_loop().run_in_executor(
            None, scraper_agent.scrape_all_groups
        )
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

        # 1. Kunlik natija
        await notification_agent.send_evening_results(
            chat_id=chat_id,
            group_name=group_name,
            solved=result["solved"],
            unsolved=result["unsolved"],
            total_given=result["total_given"],
            total_taken=result["total_taken"],
        )

        # 2. Ogohlantirish (bajarmagan o'quvchilar uchun)
        if result["warned_students"]:
            await notification_agent.send_warnings(
                group_chat_id=chat_id,
                group_name=group_name,
                warned_students=result["warned_students"],
            )

    logger.info(f"Kechqurun tekshiruv tugadi: {len(all_groups)} ta guruh")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)

    morning_h, morning_m = map(int, config.CHECK_TIME_MORNING.split(":"))
    evening_h, evening_m = map(int, config.CHECK_TIME_EVENING.split(":"))

    scheduler.add_job(morning_job, "cron", hour=morning_h, minute=morning_m, id="morning")
    scheduler.add_job(evening_job, "cron", hour=evening_h, minute=evening_m, id="evening")

    logger.info(f"Scheduler: {config.CHECK_TIME_MORNING} va {config.CHECK_TIME_EVENING} ({config.TIMEZONE})")
    return scheduler
