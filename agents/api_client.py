"""
Marsit.uz API Client — to'g'ridan-to'g'ri REST API bilan ishlaydi.
Playwright kerak emas. Faqat httpx + cookie session.

Base: https://api.marsit.uz
Auth: HttpOnly cookies (POST /api/v1/auth/signin)
"""
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from config import config

logger = logging.getLogger("api_client")

API_BASE = "https://api.marsit.uz"
SESSION_FILE = Path(config.SESSION_FILE)


def _load_cookies() -> dict | None:
    if not SESSION_FILE.exists():
        return None
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.utcnow() > expires_at:
        logger.info("Session muddati o'tgan")
        SESSION_FILE.unlink(missing_ok=True)
        return None
    return data["cookies"]


def _save_cookies(cookies: dict) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "cookies": cookies,
        "saved_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=config.SESSION_EXPIRY_HOURS)).isoformat(),
    }
    SESSION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Session saqlandi")


def _make_client(cookies: dict | None = None) -> httpx.Client:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://core.marsit.uz",
        "Referer": "https://core.marsit.uz/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
    }
    client = httpx.Client(base_url=API_BASE, headers=headers, timeout=30, follow_redirects=True)
    if cookies:
        client.cookies.update(cookies)
    return client


def _login(client: httpx.Client) -> dict:
    payload = {"user": {"phone": config.MARSIT_PHONE, "password": config.MARSIT_PASSWORD}}
    resp = client.post("/api/v1/auth/signin", json=payload)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Login xato {resp.status_code}: {resp.text[:200]}")
    cookies = dict(client.cookies)
    _save_cookies(cookies)
    logger.info("Login muvaffaqiyatli")
    return cookies


def _get_authenticated_client() -> httpx.Client:
    cookies = _load_cookies()
    client = _make_client(cookies)
    if cookies:
        resp = client.get("/api/v1/auth/check")
        if resp.status_code == 200:
            logger.info("Mavjud session faol")
            return client
        logger.info("Session eskirgan, qayta login")
    _login(client)
    return client


# ─── Public API ───────────────────────────────────────────────────────────────

def get_groups() -> list[dict]:
    """Barcha guruhlarni qaytaradi: [{id, name, students_number, ...}]"""
    client = _get_authenticated_client()
    resp = client.get("/api/v1/groups?page=1")
    resp.raise_for_status()
    data = resp.json()
    groups = data.get("groups", data) if isinstance(data, dict) else data
    logger.info(f"{len(groups)} ta guruh topildi")
    return groups


def get_today_results(group_id: int) -> list[dict]:
    """
    Bugungi uyga vazifa natijalarini qaytaradi.
    [{student_id, student_name, is_completed, score, coins_earned}]
    Agar bugun dars bo'lmasa — bo'sh ro'yxat.
    """
    today = date.today()
    client = _get_authenticated_client()
    url = f"/api/v1/groups/{group_id}/students/progress/by-lesson-days"
    resp = client.get(url, params={"year": today.year, "month": today.month})
    resp.raise_for_status()

    data = resp.json()
    lesson_days: list[dict] = data.get("lesson_days", [])

    today_str = today.isoformat()
    for day in lesson_days:
        if day.get("date") == today_str:
            logger.info(
                f"Guruh {group_id} | {today_str} | "
                f"mavzu: {day['course_element'].get('title_uz', '')} | "
                f"{len(day['students_progress'])} ta o'quvchi"
            )
            return day["students_progress"]

    logger.info(f"Guruh {group_id}: {today_str} uchun dars topilmadi")
    return []
