from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import config

_db_url = config.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
engine = create_async_engine(_db_url, echo=config.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    from models import Group, Student, CoinTransaction, CheckLog  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
