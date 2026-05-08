"""
EMIR-HUB — Marsit.uz monitoring bot
Entry point.

Ishga tushirish:
    python main.py
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):
        pass  # health check loglarini yashirish


def start_health_server() -> None:
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server port {port} da ishga tushdi")
    server.serve_forever()


async def main() -> None:
    from config import config
    from git_manager import session_start_pull
    from database import init_db
    from scheduler.scheduler import create_scheduler
    from bot.bot import create_app

    # 1. Health server (Render uyqu rejimiga tushurib qo'ymasligi uchun)
    Thread(target=start_health_server, daemon=True).start()

    # 2. Session boshida git pull
    session_start_pull()

    # 3. Config tekshirish
    config.validate()

    # 4. DB yaratish
    await init_db()
    logger.info("Database tayyor")

    # 5. Scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler ishga tushdi")

    # 6. Telegram bot
    app = create_app()
    # BUG-010: Application.bot ni notification_agent ga uzatish
    from agents.notification_agent import set_bot
    set_bot(app.bot)
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
