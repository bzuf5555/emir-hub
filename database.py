from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import config
import logging

logger = logging.getLogger("database")

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        # BUG-021: timeout qo'shildi — hang oldini olish
        _client = AsyncIOMotorClient(
            config.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[config.MONGODB_DB]


async def init_db() -> None:
    db = get_db()
    # BUG-021: ulanish tekshiruvi
    await get_client().admin.command("ping")
    logger.info("MongoDB ulanish tasdiqlandi")

    await db.groups.create_index("marsit_id", unique=True)
    await db.students.create_index("marsit_id", unique=True)
    await db.students.create_index("group_id")
    # BUG-023: qo'shimcha indexlar
    await db.check_logs.create_index([("group_id", 1), ("checked_at", -1)])
    await db.coin_transactions.create_index("student_marsit_id")
    await db.coin_transactions.create_index("created_at")
