import logging
from datetime import datetime, timezone

from database import get_db
from config import config

logger = logging.getLogger("coin_agent")


async def process_results(group_marsit_id: str, student_results: list[dict]) -> dict:
    """
    student_results: [{"marsit_id": str, "name": str, "solved": bool}, ...]
    Qaytaradi: {"solved": [...], "unsolved": [...], "total_given": int, "total_taken": int}
    """
    db = get_db()
    solved, unsolved = [], []
    total_given = total_taken = 0
    transactions = []
    now = datetime.now(timezone.utc)

    for sr in student_results:
        is_solved = sr["solved"]
        coins = config.COIN_SOLVED if is_solved else config.COIN_UNSOLVED
        student_name = sr["name"]
        marsit_id = sr["marsit_id"]

        await db.students.update_one(
            {"marsit_id": marsit_id},
            {
                "$set": {"name": student_name, "group_id": group_marsit_id, "is_active": True},
                "$inc": {"coin_balance": coins},
            },
            upsert=True,
        )

        transactions.append({
            "student_marsit_id": marsit_id,
            "student_name": student_name,
            "amount": coins,
            "reason": f"Vazifa {'bajarildi' if is_solved else 'bajarilmadi'} ({now.date()})",
            "created_at": now,
        })

        if is_solved:
            solved.append({"name": student_name, "marsit_id": marsit_id})
            total_given += coins
        else:
            unsolved.append({"name": student_name, "marsit_id": marsit_id})
            total_taken += abs(coins)

        logger.info(f"{student_name}: {'+' if coins > 0 else ''}{coins} coin")

    if transactions:
        await db.coin_transactions.insert_many(transactions)

    await db.check_logs.insert_one({
        "group_id": group_marsit_id,
        "check_type": "evening",
        "solved_count": len(solved),
        "unsolved_count": len(unsolved),
        "checked_at": now,
    })

    return {"solved": solved, "unsolved": unsolved, "total_given": total_given, "total_taken": total_taken}


async def get_leaderboard(limit: int = 20) -> list[dict]:
    db = get_db()
    cursor = db.students.find({"is_active": True}, {"name": 1, "coin_balance": 1}).sort("coin_balance", -1).limit(limit)
    return await cursor.to_list(length=limit)
