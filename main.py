"""
EMIR-HUB — Marsit.uz monitoring bot
Entry point.

Ishga tushirish:
    python main.py
"""
import asyncio
import logging
import sys
from pathlib import Path

# Logging sozlash
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/main.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


async def main() -> None:
    from config import config
    from git_manager import session_start_pull
    from database import init_db
    from scheduler.scheduler import create_scheduler
    from bot.bot import create_app

    # 1. Session boshida git pull
    session_start_pull()

    # 2. Config tekshirish
    config.validate()

    # 3. DB yaratish
    await init_db()
    logger.info("Database tayyor")

    # 4. Scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler ishga tushdi")

    # 5. Telegram bot
    app = create_app()
    logger.info("Bot ishga tushmoqda...")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot ishlayapti. To'xtatish uchun Ctrl+C")

        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("To'xtatilmoqda...")
        finally:
            scheduler.shutdown(wait=False)
            await app.updater.stop()
            await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
