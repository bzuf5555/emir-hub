from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from config import config

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(config.MONGODB_URI)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[config.MONGODB_DB]


async def init_db() -> None:
    db = get_db()
    await db.groups.create_index("marsit_id", unique=True)
    await db.students.create_index("marsit_id", unique=True)
    await db.students.create_index("group_id")
    await db.check_logs.create_index("group_id")
