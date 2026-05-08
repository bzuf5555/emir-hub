"""
Marsit.uz API Client — to'g'ridan-to'g'ri REST API.
Auth: HttpOnly cookies (POST /api/v1/auth/signin)
"""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from config import config

logger = logging.getLogger("api_client")

API_BASE  = "https://api.marsit.uz"
SESSION_FILE = Path(config.SESSION_FILE)

# BUG-001: bitta shared client — har chaqiruvda yangi client yaratilmaydi
_shared_client: httpx.Client | None = None


def _load_cookies() -> dict | None:
    if not SESSION_FILE.exists():
        return None
    data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    # BUG-013: utcnow() o'rniga timezone-aware
    expires_at = datetime.fromisoformat(data["expires_at"])
    if datetime.now(timezone.utc).replace(tzinfo=None) > expires_at:
        logger.info("Session muddati o'tgan")
        SESSION_FILE.unlink(missing_ok=True)
        return None
    return data["cookies"]


def _save_cookies(cookies: dict) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # BUG-013
    data = {
        "cookies": cookies,
        "saved_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=config.SESSION_EXPIRY_HOURS)).isoformat(),
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


def _login(client: httpx.Client) -> None:
    payload = {"user": {"phone": config.MARSIT_PHONE, "password": config.MARSIT_PASSWORD}}
    resp = client.post("/api/v1/auth/signin", json=payload)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Login xato {resp.status_code}: {resp.text[:200]}")
    _save_cookies(dict(client.cookies))
    logger.info("Login muvaffaqiyatli")


def get_client() -> httpx.Client:
    """BUG-001: bitta authenticated client qaytaradi, login kerak bo'lsa qiladi."""
    global _shared_client
    cookies = _load_cookies()

    if _shared_client is None:
        _shared_client = _make_client(cookies)

    if cookies:
        resp = _shared_client.get("/api/v1/auth/check")
        if resp.status_code == 200:
            return _shared_client
        logger.info("Session eskirgan, qayta login")

    _login(_shared_client)
    return _shared_client


# ─── Public API ───────────────────────────────────────────────────────────────

def get_groups() -> list[dict]:
    """Barcha guruhlarni qaytaradi. BUG-004: pagination qo'llab-quvvatlash."""
    client = get_client()
    all_groups = []
    page = 1
    while True:
        resp = client.get(f"/api/v1/groups?page={page}")
        resp.raise_for_status()
        data = resp.json()
        groups = data.get("groups", []) if isinstance(data, dict) else data
        all_groups.extend(groups)

        page_count = data.get("page_count", 1) if isinstance(data, dict) else 1
        if page >= page_count:
            break
        page += 1

    logger.info(f"{len(all_groups)} ta guruh topildi ({page} sahifa)")
    return all_groups


def get_today_results(group_id: int) -> list[dict]:
    """Bugungi uyga vazifa natijalari: [{student_id, student_name, is_completed, ...}]"""
    today = date.today()
    client = get_client()
    resp = client.get(
        f"/api/v1/groups/{group_id}/students/progress/by-lesson-days",
        params={"year": today.year, "month": today.month}
    )
    resp.raise_for_status()

    today_str = today.isoformat()
    for day in resp.json().get("lesson_days", []):
        if day.get("date") == today_str:
            element  = day.get("course_element") or {}  # BUG-019
            progress = day.get("students_progress", [])  # BUG-019
            logger.info(f"Guruh {group_id} | {today_str} | {element.get('title_uz','')} | {len(progress)} ta")
            return progress

    logger.info(f"Guruh {group_id}: {today_str} dars topilmadi")
    return []


def get_today_lesson_info(group_id: int) -> dict | None:
    """Bugungi dars: {date, course_element, students_progress}"""
    today = date.today()
    client = get_client()
    resp = client.get(
        f"/api/v1/groups/{group_id}/students/progress/by-lesson-days",
        params={"year": today.year, "month": today.month}
    )
    resp.raise_for_status()
    today_str = today.isoformat()
    for day in resp.json().get("lesson_days", []):
        if day.get("date") == today_str:
            return day
    return None


def assign_task_to_group(group_id: int, course_element_ids: list[int], student_ids: list[int]) -> bool:
    """POST /api/v2/controls/booking/add-task"""
    client = get_client()
    resp = client.post(
        "/api/v2/controls/booking/add-task",
        json={"group_id": group_id, "student_ids": student_ids, "course_element_ids": course_element_ids},
    )
    if resp.status_code in (200, 201):
        logger.info(f"Guruh {group_id}: topshiriq berildi — {len(student_ids)} o'quvchi")
        return True
    logger.error(f"Topshiriq berish xato {resp.status_code}: {resp.text[:200]}")
    return False
