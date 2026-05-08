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
            # BUG-019: .get() bilan KeyError himoyasi
            element = day.get("course_element") or {}
            progress = day.get("students_progress", [])
            logger.info(
                f"Guruh {group_id} | {today_str} | "
                f"mavzu: {element.get('title_uz', '')} | "
                f"{len(progress)} ta o'quvchi"
            )
            return progress

    logger.info(f"Guruh {group_id}: {today_str} uchun dars topilmadi")
    return []


def get_today_lesson_info(group_id: int) -> dict | None:
    """
    Bugungi dars ma'lumotini qaytaradi:
    {course_element: {id, title_uz}, students_progress: [...]}
    """
    today = date.today()
    client = _get_authenticated_client()
    url = f"/api/v1/groups/{group_id}/students/progress/by-lesson-days"
    resp = client.get(url, params={"year": today.year, "month": today.month})
    resp.raise_for_status()

    lesson_days: list[dict] = resp.json().get("lesson_days", [])
    today_str = today.isoformat()
    for day in lesson_days:
        if day.get("date") == today_str:
            return day
    return None


def get_group_students(group_id: int) -> list[dict]:
    """Guruhning barcha o'quvchilarini qaytaradi: [{id, ...}]"""
    client = _get_authenticated_client()
    resp = client.get(f"/api/v1/groups/{group_id}?group_id={group_id}&all=false")
    resp.raise_for_status()
    data = resp.json()
    # O'quvchilar attendance dan olinadi
    attendance_resp = client.get(
        f"/api/v1/attendance/{group_id}",
        params={"group_id": group_id, "from_date": date.today().replace(day=1).isoformat(),
                "till_date": date.today().isoformat(), "all": "false"}
    )
    if attendance_resp.status_code == 200:
        att_data = attendance_resp.json()
        students = att_data.get("students", [])
        if students:
            return students
    # Fallback: progress dan olinadi
    progress_resp = client.get(
        f"/api/v1/groups/{group_id}/students/progress/by-lesson-days",
        params={"year": date.today().year, "month": date.today().month}
    )
    if progress_resp.status_code == 200:
        lesson_days = progress_resp.json().get("lesson_days", [])
        if lesson_days:
            return [{"id": s["student_id"], "name": s["student_name"]}
                    for s in lesson_days[0].get("students_progress", [])]
    return []


def assign_task_to_group(group_id: int, course_element_ids: list[int], student_ids: list[int]) -> bool:
    """
    Guruhga topshiriq beradi.

    API: POST /api/v2/controls/booking/add-task
    Body: {"group_id": int, "student_ids": [...], "course_element_ids": [...]}
    """
    client = _get_authenticated_client()
    payload = {
        "group_id": group_id,
        "student_ids": student_ids,
        "course_element_ids": course_element_ids,
    }
    resp = client.post("/api/v2/controls/booking/add-task", json=payload)
    if resp.status_code in (200, 201):
        logger.info(f"Guruh {group_id}: topshiriq berildi. elements={course_element_ids}, students={len(student_ids)}")
        return True
    logger.error(f"Topshiriq berish xato {resp.status_code}: {resp.text[:200]}")
    return False
