import logging
from datetime import datetime, timedelta, timezone

from database import get_db
from config import config

logger = logging.getLogger("coin_agent")


async def process_results(
    group_marsit_id: str,
    student_results: list[dict],
    check_type: str = "evening",  # BUG-011: "morning" | "evening" | "manual"
) -> dict:
    """
    student_results: [{"marsit_id": str, "name": str, "solved": bool}, ...]
    Qaytaradi: {solved, unsolved, total_given, total_taken, warned_students}
    """
    db = get_db()
    now = datetime.now(timezone.utc)

    # BUG-002: bugun allaqachon tekshirilganmi?
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    existing = await db.check_logs.find_one({
        "group_id": group_marsit_id,
        "check_type": check_type,
        "checked_at": {"$gte": today_start},
    })
    if existing:
        logger.warning(f"Guruh {group_marsit_id}: bugun ({check_type}) allaqachon tekshirilgan — o'tkazib yuborildi")
        return {"solved": [], "unsolved": [], "total_given": 0, "total_taken": 0, "warned_students": []}

    solved, unsolved, warned_students = [], [], []
    total_given = total_taken = 0
    transactions = []

    for sr in student_results:
        is_solved = sr["solved"]
        coins = config.COIN_SOLVED if is_solved else config.COIN_UNSOLVED
        name = sr["name"]
        marsit_id = sr["marsit_id"]

        if is_solved:
            await db.students.update_one(
                {"marsit_id": marsit_id},
                {
                    "$set": {"name": name, "group_id": group_marsit_id, "is_active": True, "missed_streak": 0},
                    "$inc": {"coin_balance": coins},
                },
                upsert=True,
            )
            solved.append({"name": name, "marsit_id": marsit_id})
            total_given += coins
        else:
            result = await db.students.find_one_and_update(
                {"marsit_id": marsit_id},
                {
                    "$set": {"name": name, "group_id": group_marsit_id, "is_active": True},
                    "$inc": {"coin_balance": coins, "missed_streak": 1},
                },
                upsert=True,
                return_document=True,
            )
            streak = ((result or {}).get("missed_streak", 0) + 1) if result else 1

            unsolved.append({"name": name, "marsit_id": marsit_id})
            warned_students.append({"name": name, "marsit_id": marsit_id, "missed_streak": streak})
            total_taken += abs(coins)

        transactions.append({
            "student_marsit_id": marsit_id,
            "student_name": name,
            "amount": coins,
            "reason": f"Vazifa {'bajarildi' if is_solved else 'bajarilmadi'} ({now.date()})",
            "created_at": now,
        })
        logger.info(f"{name}: {'+' if coins > 0 else ''}{coins} coin")

    if transactions:
        await db.coin_transactions.insert_many(transactions)

    await db.check_logs.insert_one({
        "group_id": group_marsit_id,
        "check_type": check_type,
        "solved_count": len(solved),
        "unsolved_count": len(unsolved),
        "checked_at": now,
    })

    return {
        "solved": solved,
        "unsolved": unsolved,
        "total_given": total_given,
        "total_taken": total_taken,
        "warned_students": warned_students,
    }


async def get_leaderboard(limit: int = 20) -> list[dict]:
    db = get_db()
    cursor = db.students.find(
        {"is_active": True}, {"name": 1, "coin_balance": 1}
    ).sort("coin_balance", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_weekly_stats(group_marsit_id: str) -> dict:
    """
    O'tgan 7 kun uchun guruh statistikasini qaytaradi.

    Qaytaradi:
    {
      "week_start": date, "week_end": date,
      "check_days": int,                     # necha kun tekshirilgan
      "group_avg_pct": float,                # guruh o'rtacha %
      "total_given": int, "total_taken": int,
      "students": [
          {"name", "completed", "missed", "coins_earned", "coins_lost"},
          ...
      ]
    }
    """
    db = get_db()
    now     = datetime.now(timezone.utc)
    week_end   = now.replace(hour=23, minute=59, second=59)
    week_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Hafta davomidagi barcha tranzaksiyalar (guruh o'quvchilari)
    students_in_group = await db.students.find(
        {"group_id": group_marsit_id, "is_active": True},
        {"marsit_id": 1, "name": 1, "coin_balance": 1}
    ).to_list(length=200)

    marsit_ids = [s["marsit_id"] for s in students_in_group]
    student_map = {s["marsit_id"]: s["name"] for s in students_in_group}

    txs = await db.coin_transactions.find({
        "student_marsit_id": {"$in": marsit_ids},
        "created_at": {"$gte": week_start, "$lte": week_end},
    }).to_list(length=5000)

    # Har o'quvchi uchun hisob
    stats: dict[str, dict] = {}
    for mid in marsit_ids:
        stats[mid] = {"name": student_map[mid], "completed": 0, "missed": 0,
                      "coins_earned": 0, "coins_lost": 0}

    for tx in txs:
        mid = tx["student_marsit_id"]
        if mid not in stats:
            continue
        if tx["amount"] > 0:
            stats[mid]["completed"] += 1
            stats[mid]["coins_earned"] += tx["amount"]
        else:
            stats[mid]["missed"] += 1
            stats[mid]["coins_lost"] += abs(tx["amount"])

    # Tekshirilgan kunlar soni (check_logs)
    logs = await db.check_logs.find({
        "group_id": group_marsit_id,
        "check_type": "evening",
        "checked_at": {"$gte": week_start},
    }).to_list(length=50)
    check_days = len(logs)

    students_list = sorted(stats.values(), key=lambda x: x["completed"], reverse=True)

    total_checks = check_days * len(marsit_ids) if check_days and marsit_ids else 0
    total_completed = sum(s["completed"] for s in students_list)
    group_avg = round(total_completed / total_checks * 100, 1) if total_checks else 0.0

    return {
        "week_start": week_start.date(),
        "week_end": week_end.date(),
        "check_days": check_days,
        "group_avg_pct": group_avg,
        "total_given": sum(s["coins_earned"] for s in students_list),
        "total_taken": sum(s["coins_lost"] for s in students_list),
        "students": students_list,
    }
