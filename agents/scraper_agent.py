"""
Scraper Agent — marsit.uz teacher dashboard dan ma'lumot oladi.

Oqim:
  1. Browser ochiladi
  2. Session (cookies) yuklanadi
  3. Session eskirgan bo'lsa → yangi login
  4. Guruhlar ro'yxati olinadi
  5. Har guruh uchun o'quvchilar va vazifa statusi olinadi
"""
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext

from agents import token_agent
from config import config

logger = logging.getLogger("scraper_agent")


@dataclass
class StudentResult:
    marsit_id: str
    name: str
    solved: bool


@dataclass
class GroupData:
    marsit_id: str
    name: str
    students: list[StudentResult] = field(default_factory=list)


async def _screenshot(page: Page, name: str) -> None:
    if not config.SCREENSHOT_ON_ERROR:
        return
    os.makedirs("screenshots", exist_ok=True)
    path = f"screenshots/{name}_{date.today()}.png"
    await page.screenshot(path=path, full_page=True)
    logger.info(f"Screenshot: {path}")


async def _login(page: Page, context: BrowserContext) -> None:
    """
    Marsit.uz login: telefon raqam + parol.
    Login sahifasi: https://core.marsit.uz/ (root)
    Selectors Playwright snapshot dan aniqlangan: 2026-05-07
    """
    logger.info("Login qilinmoqda...")
    await page.goto(config.MARSIT_BASE_URL, wait_until="networkidle", timeout=30000)
    await _screenshot(page, "before_login")

    # Telefon raqam field — "+998" pre-filled, triple-click bilan tanlab tozalab yozamiz
    phone_input = page.get_by_placeholder("Telefon raqam")
    await phone_input.wait_for(state="visible", timeout=10000)
    await phone_input.triple_click()
    await phone_input.fill(config.MARSIT_PHONE)

    # Parol field
    password_input = page.get_by_placeholder("Password")
    await password_input.fill(config.MARSIT_PASSWORD)

    # "Kirish" tugmasi (disabled → enabled bo'lishini kutamiz)
    kirish_btn = page.get_by_role("button", name="Kirish")
    await kirish_btn.wait_for(state="enabled", timeout=5000)
    await kirish_btn.click()

    await page.wait_for_load_state("networkidle", timeout=20000)

    # Hali login sahifasida qolgan bo'lsa — xato
    if page.url.rstrip("/") == config.MARSIT_BASE_URL.rstrip("/"):
        await _screenshot(page, "login_failed")
        raise RuntimeError("Login muvaffaqiyatsiz — telefon raqam yoki parolni tekshiring")

    cookies = await context.cookies()
    token_agent.save_session(cookies)
    logger.info(f"Login muvaffaqiyatli → {page.url}")


async def _ensure_authenticated(page: Page, context: BrowserContext) -> None:
    session_applied = await token_agent.apply_session(context)
    if session_applied:
        if await token_agent.is_session_valid(page):
            return

    await _login(page, context)


async def _get_groups(page: Page) -> list[dict]:
    """Dashboard dan guruhlar ro'yxatini oladi."""
    await page.goto(config.MARSIT_DASHBOARD_URL, wait_until="networkidle", timeout=30000)
    await _screenshot(page, "dashboard")

    # Marsit.uz dagi guruhlar API orqali yuklanadi — intercepting network
    groups_data: list[dict] = []

    async def intercept_response(response):
        if "group" in response.url.lower() and response.status == 200:
            try:
                body = await response.json()
                if isinstance(body, list) and body:
                    groups_data.extend(body)
                elif isinstance(body, dict) and "data" in body:
                    groups_data.extend(body["data"])
            except Exception:
                pass

    page.on("response", intercept_response)

    # Sahifani refresh qilib API so'rovlarni ushlaymiz
    await page.reload(wait_until="networkidle", timeout=30000)
    await asyncio.sleep(2)

    page.remove_listener("response", intercept_response)

    if not groups_data:
        # Fallback: DOM dan o'qish
        groups_data = await _extract_groups_from_dom(page)

    logger.info(f"{len(groups_data)} ta guruh topildi")
    return groups_data


async def _extract_groups_from_dom(page: Page) -> list[dict]:
    """Agar API intercept ishlamasa — DOM dan guruhlarni oladi."""
    await _screenshot(page, "groups_dom_fallback")
    return await page.evaluate("""
        () => {
            const items = [];
            // Guruh elementlarini qidirish (various selectors)
            const selectors = [
                '[class*="group"]',
                '[class*="Group"]',
                '[data-type="group"]',
                'li[class*="item"]'
            ];
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                if (els.length > 0) {
                    els.forEach(el => {
                        const id = el.getAttribute('data-id') || el.id || '';
                        const name = el.textContent?.trim() || '';
                        if (id || name) items.push({ id, name });
                    });
                    break;
                }
            }
            return items;
        }
    """)


async def _get_homework_results(page: Page, group_id: str, group_url: str) -> list[StudentResult]:
    """Berilgan guruhning uyga vazifa natijalarini oladi."""
    logger.info(f"Guruh {group_id} tekshirilmoqda: {group_url}")

    results: list[StudentResult] = []

    async def intercept(response):
        url = response.url.lower()
        if ("homework" in url or "task" in url or "vazifa" in url) and response.status == 200:
            try:
                body = await response.json()
                students = body if isinstance(body, list) else body.get("data", [])
                for s in students:
                    name = s.get("name") or s.get("fullName") or s.get("full_name") or ""
                    sid = str(s.get("id") or s.get("studentId") or "")
                    solved = bool(s.get("solved") or s.get("completed") or s.get("isDone") or s.get("status") == "done")
                    if name:
                        results.append(StudentResult(marsit_id=sid, name=name, solved=solved))
            except Exception:
                pass

    page.on("response", intercept)
    await page.goto(group_url, wait_until="networkidle", timeout=30000)
    await asyncio.sleep(3)
    page.remove_listener("response", intercept)

    if not results:
        results = await _extract_results_from_dom(page, group_id)

    logger.info(f"Guruh {group_id}: {len(results)} ta o'quvchi")
    return results


async def _extract_results_from_dom(page: Page, group_id: str) -> list[StudentResult]:
    """Fallback: DOM dan o'quvchi natijalarini oladi."""
    await _screenshot(page, f"results_dom_{group_id}")
    raw = await page.evaluate("""
        () => {
            const rows = [];
            const table = document.querySelector('table, [class*="table"], [class*="list"]');
            if (!table) return rows;
            const items = table.querySelectorAll('tr, [class*="row"], [class*="item"]');
            items.forEach(item => {
                const cells = item.querySelectorAll('td, [class*="cell"], [class*="col"]');
                if (cells.length >= 2) {
                    rows.push({
                        name: cells[0].textContent?.trim() || '',
                        status: item.innerHTML || ''
                    });
                }
            });
            return rows;
        }
    """)

    results = []
    for row in raw:
        name = row.get("name", "").strip()
        if not name:
            continue
        status_html = row.get("status", "").lower()
        # Turli ko'rinishdagi "bajarildi" belgilarini topish
        solved = any(marker in status_html for marker in [
            "✅", "done", "completed", "solved", "bajarildi", "check", "success", "green"
        ])
        results.append(StudentResult(marsit_id="", name=name, solved=solved))

    return results


async def scrape_all_groups() -> list[GroupData]:
    """Asosiy publick funksiya — barcha guruhlar natijasini qaytaradi."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not config.DEBUG)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"
        )
        page = await context.new_page()

        try:
            await _ensure_authenticated(page, context)
            raw_groups = await _get_groups(page)

            all_groups: list[GroupData] = []
            for g in raw_groups:
                gid = str(g.get("id", g.get("marsit_id", "")))
                gname = g.get("name", g.get("title", f"Guruh {gid}"))
                group_url = g.get("url") or f"{config.MARSIT_DASHBOARD_URL}?group={gid}"

                students = await _get_homework_results(page, gid, group_url)
                all_groups.append(GroupData(marsit_id=gid, name=gname, students=students))

            return all_groups

        except Exception as e:
            logger.error(f"Scraping xato: {e}")
            await _screenshot(page, "scraping_error")
            raise
        finally:
            await browser.close()
