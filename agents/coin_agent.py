import logging
from datetime import datetime, timezone

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
