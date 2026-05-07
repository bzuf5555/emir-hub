import json
import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from agents import scraper_agent, coin_agent, notification_agent
from config import config
from database import AsyncSessionLocal
from models import Group, CheckLog

logger = logging.getLogger("scheduler")
tz = pytz.timezone(config.TIMEZONE)


async def morning_job() -> None:
    """09:00 — eslatma yuborish."""
    logger.info("Ertalab eslatma job boshlandi")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Group).where(Group.is_active == True, Group.telegram_chat_id != None)
        )
        groups = result.scalars().all()

    for group in groups:
        await notification_agent.send_morning_reminder(group.telegram_chat_id, group.name)

    logger.info(f"Ertalab eslatma {len(groups)} ta guruhga yuborildi")


async def evening_job() -> None:
    """23:00 — test natijalarini tekshirish va yuborish."""
    logger.info("Kechqurun tekshiruv job boshlandi")

    try:
        all_groups = await scraper_agent.scrape_all_groups()
    except Exception as e:
        logger.error(f"Scraping muvaffaqiyatsiz: {e}")
        return

    async with AsyncSessionLocal() as session:
        db_groups = await session.execute(select(Group).where(Group.is_active == True))
        db_groups_map = {g.marsit_id: g for g in db_groups.scalars().all()}

        for group_data in all_groups:
            student_dicts = [
                {"marsit_id": s.marsit_id, "name": s.name, "solved": s.solved}
                for s in group_data.students
            ]

            result = await coin_agent.process_results(session, group_data.marsit_id, student_dicts)
            group = result["group"]

            log = CheckLog(
                group_id=group.id,
                check_type="evening",
                results_json=json.dumps(student_dicts, ensure_ascii=False),
                solved_count=len(result["solved"]),
                unsolved_count=len(result["unsolved"]),
            )
            session.add(log)

            if group.telegram_chat_id:
                await notification_agent.send_evening_results(
                    chat_id=group.telegram_chat_id,
                    group_name=group.name,
                    solved=result["solved"],
                    unsolved=result["unsolved"],
                    total_given=result["total_given"],
                    total_taken=result["total_taken"],
                )

        await session.commit()

    logger.info(f"Kechqurun tekshiruv tugadi: {len(all_groups)} ta guruh")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)

    morning_h, morning_m = map(int, config.CHECK_TIME_MORNING.split(":"))
    evening_h, evening_m = map(int, config.CHECK_TIME_EVENING.split(":"))

    scheduler.add_job(morning_job, "cron", hour=morning_h, minute=morning_m, id="morning")
    scheduler.add_job(evening_job, "cron", hour=evening_h, minute=evening_m, id="evening")

    logger.info(f"Scheduler sozlandi: {config.CHECK_TIME_MORNING} va {config.CHECK_TIME_EVENING} ({config.TIMEZONE})")
    return scheduler
