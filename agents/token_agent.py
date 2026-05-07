import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from playwright.async_api import BrowserContext

from config import config

logger = logging.getLogger("token_agent")


def _session_path() -> str:
    return config.SESSION_FILE


def save_session(cookies: list[dict], storage_state: dict | None = None) -> None:
    os.makedirs(os.path.dirname(_session_path()), exist_ok=True)
    data = {
        "cookies": cookies,
        "storage_state": storage_state,
        "saved_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=config.SESSION_EXPIRY_HOURS)).isoformat(),
    }
    with open(_session_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info("Session saqlandi")


def load_session() -> Optional[dict]:
    if not os.path.exists(_session_path()):
        return None

    with open(_session_path(), "r", encoding="utf-8") as f:
        data = json.load(f)

    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.utcnow() > expires_at:
        logger.info("Session muddati o'tgan, yangi login kerak")
        clear_session()
        return None

    logger.info("Session yuklandi (hali faol)")
    return data


async def apply_session(context: BrowserContext) -> bool:
    """Yuklab olingan cookilarni brauzer kontekstiga qo'llaydi. True = muvaffaqiyatli."""
    data = load_session()
    if not data:
        return False

    await context.add_cookies(data["cookies"])
    return True


async def is_session_valid(page) -> bool:
    """Dashboard sahifasini yuklaydi va login redirect yo'qligini tekshiradi."""
    await page.goto(config.MARSIT_DASHBOARD_URL, wait_until="domcontentloaded", timeout=15000)
    current_url = page.url
    is_valid = "/login" not in current_url and "/auth" not in current_url
    logger.info(f"Session tekshiruvi: {'faol' if is_valid else 'eskirgan'} ({current_url})")
    return is_valid


def clear_session() -> None:
    if os.path.exists(_session_path()):
        os.remove(_session_path())
        logger.info("Session o'chirildi")
