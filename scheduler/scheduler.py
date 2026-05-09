import asyncio
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from agents import coin_agent, notification_agent
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
    """
    23:00 — Topshiriqlar → Berilgan topshiriqlar dan natija + coin + ogohlantirish.
    tasks-teacher + student_projects endpointlari ishlatiladi.
    """
    logger.info("23:00 job boshlandi")

    from agents.api_client import get_any_student_id, get_tasks_for_student, get_element_submissions

    db = get_db()
    groups = await db.groups.find(
        {"is_active": True, "telegram_chat_id": {"$exists": True, "$ne": None}}
    ).to_list(length=50)

    for group in groups:
        marsit_id  = group["marsit_id"]
        group_name = group.get("name", marsit_id)
        chat_id    = group["telegram_chat_id"]

        try:
            # 1. Bitta student_id olish
            student_doc = await db.students.find_one({"group_id": marsit_id})
            if student_doc:
                student_id = int(student_doc["marsit_id"])
            else:
                student_id = await _run_sync(get_any_student_id, int(marsit_id))

            if not student_id:
                logger.info(f"{group_name}: o'quvchi topilmadi, o'tkazib yuborildi")
                continue

            # 2. Berilgan topshiriqlarni olish
            tasks = await _run_sync(get_tasks_for_student, int(marsit_id), student_id)
            if not tasks:
                logger.info(f"{group_name}: topshiriq berilmagan, o'tkazib yuborildi")
                continue

            # 3. Har topshiriq uchun submissions
            all_students: dict[int, dict] = {}  # student_id → {name, solved}
            for task in tasks:
                submissions = await _run_sync(
                    get_element_submissions, int(marsit_id), task["id"]
                )
                for s in submissions:
                    sid  = s["id"]
                    name = f"{s.get('first_name','')} {s.get('last_name','')}".strip()
                    if sid not in all_students:
                        all_students[sid] = {"name": name, "marsit_id": str(sid), "solved": False}
                    if s.get("answer") is not None:
                        all_students[sid]["solved"] = True

            if not all_students:
                logger.info(f"{group_name}: submissions bo'sh")
                continue

            # 4. Coin hisob-kitob
            student_dicts = list(all_students.values())
            result = await coin_agent.process_results(marsit_id, student_dicts, check_type="evening")

            # 5. Guruh chatiga natija
            await notification_agent.send_evening_results(
                chat_id=chat_id, group_name=group_name,
                solved=result["solved"], unsolved=result["unsolved"],
                total_given=result["total_given"], total_taken=result["total_taken"],
            )

            # 6. Ogohlantirish
            if result["warned_students"]:
                await notification_agent.send_warnings(
                    group_chat_id=chat_id,
                    group_name=group_name,
                    warned_students=result["warned_students"],
                )

            logger.info(f"{group_name}: {len(result['solved'])} bajardi, {len(result['unsolved'])} bajarmadi")

        except Exception as e:
            logger.error(f"{group_name} evening_job xato: {e}")

    logger.info("23:00 job tugadi")


# ─── Scheduler ────────────────────────────────────────────────────────────────

async def weekly_report_job() -> None:
    """Har dushanba 09:00 — haftalik hisobot mentorga."""
    if not config.MENTOR_CHAT_ID:
        logger.warning("MENTOR_CHAT_ID sozlanmagan — haftalik hisobot o'tkazib yuborildi")
        return

    logger.info("Haftalik hisobot job boshlandi")

    try:
        from agents.api_client import get_groups as _get_groups
        raw_groups = await _run_sync(_get_groups)
    except Exception as e:
        logger.error(f"Guruhlar olishda xato: {e}")
        return

    from agents.coin_agent import get_weekly_stats

    for g in raw_groups:
        try:
            stats = await get_weekly_stats(str(g["id"]))
            if stats["check_days"] == 0:
                logger.info(f"Guruh {g['name']}: hafta davomida tekshiruv yo'q, o'tkazib yuborildi")
                continue
            await notification_agent.send_weekly_report(
                chat_id=config.MENTOR_CHAT_ID,
                group_name=g.get("name", str(g["id"])),
                stats=stats,
            )
        except Exception as e:
            logger.error(f"Guruh {g['id']} haftalik hisobot xato: {e}")

    logger.info("Haftalik hisobot yuborildi")


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=tz)

    morning_h, morning_m = map(int, config.CHECK_TIME_MORNING.split(":"))
    evening_h, evening_m = map(int, config.CHECK_TIME_EVENING.split(":"))

    # 09:00 — eslatma + topshiriq taklifi + bajarmagan ro'yxat
    scheduler.add_job(morning_job,            "cron", hour=morning_h, minute=morning_m, id="morning")
    scheduler.add_job(unsubmitted_report_job, "cron", hour=morning_h, minute=morning_m, id="unsubmitted_9")

    # 10:00 — bajarmagan ro'yxat (ikkinchi eslatma)
    scheduler.add_job(unsubmitted_report_job, "cron", hour=10, minute=0, id="unsubmitted_10")

    # 23:00 — natijalar
    scheduler.add_job(evening_job,            "cron", hour=evening_h, minute=evening_m, id="evening")

    # Har dushanba 09:00 — haftalik hisobot
    scheduler.add_job(weekly_report_job,      "cron", day_of_week="mon",
                      hour=morning_h, minute=morning_m, id="weekly")

    logger.info(
        f"Scheduler: {config.CHECK_TIME_MORNING} (dushanba: haftalik hisobot ham), "
        f"10:00, {config.CHECK_TIME_EVENING} ({config.TIMEZONE})"
    )
    return scheduler
