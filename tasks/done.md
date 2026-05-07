# BAJARILGAN TASKLAR

---

## T-100-001 · Loyiha tuzilmasi va config fayllari
**Model:** `claude-haiku-4-5-20251001` | **Tugatildi:** 2026-05-07

- [x] T-100-001-1 · CLAUDE.md — 12 ta qatiy qoida yozildi
- [x] T-100-001-2 · `.env.example` yaratildi
- [x] T-100-001-3 · `requirements.txt` yozildi
- [x] T-100-001-4 · `.gitignore` sozlandi
- [x] T-100-001-5 · `config.py` — `.env` loader va validate()

---

## T-200-002 · Database modellari
**Model:** `claude-sonnet-4-6` | **Tugatildi:** 2026-05-07

- [x] T-200-002-1 · `Student` modeli (marsit_id, name, coin_balance, is_active)
- [x] T-200-002-2 · `Group` modeli (marsit_id, name, telegram_chat_id)
- [x] T-200-002-3 · `CoinTransaction` modeli (student_id, amount, reason)
- [x] T-200-002-4 · `CheckLog` modeli (group_id, check_type, results_json)
- [x] T-200-002-5 · `database.py` — async SQLite + SQLAlchemy 2.0

---

## T-100-003 · Git Manager
**Model:** `claude-haiku-4-5-20251001` | **Tugatildi:** 2026-05-07

- [x] T-100-003-1 · `session_start_pull()` — session boshida git pull
- [x] T-100-003-2 · `task_done_push()` — task tuganda git push
- [x] T-100-003-3 · Conflict avtomatik resolve

---

## T-200-004 · Token Agent — session saqlash
**Model:** `claude-sonnet-4-6` | **Tugatildi:** 2026-05-07

- [x] T-200-004-1 · `save_session()` — cookies.json ga yozish
- [x] T-200-004-2 · `load_session()` — yuklab Playwright ga apply
- [x] T-200-004-3 · `is_session_valid()` — dashboard yuklanadi/loginmi tekshirish
- [x] T-200-004-4 · `clear_session()` — eski cookies o'chirish

**Data:** `session/cookies.json`, 12 soat muddati

---

## T-300-005 · Scraper Agent — marsit.uz scraping
**Model:** `claude-opus-4-7` | **Tugatildi:** 2026-05-07

- [x] T-300-005-1 · Login flow (email + parol, Enter yuborish)
- [x] T-300-005-2 · Guruhlar ro'yxatini olish (API intercept + DOM fallback)
- [x] T-300-005-3 · Guruh ichidagi o'quvchilar
- [x] T-300-005-4 · Uyga vazifa completion status
- [x] T-300-005-5 · Debug screenshot rejimi (`SCREENSHOT_ON_ERROR=true`)
- [x] T-300-005-6 · Retry va error handling

**Data:** `https://core.marsit.uz/teacher-dashboard`, "uyga vazifalar" bo'limi

---

## T-100-006 · Coin Agent — hisob-kitob
**Model:** `claude-haiku-4-5-20251001` | **Tugatildi:** 2026-05-07

- [x] T-100-006-1 · Bajargan: `+5 coin`
- [x] T-100-006-2 · Bajarmagan: `-20 coin`
- [x] T-100-006-3 · `CoinTransaction` DB ga yozish
- [x] T-100-006-4 · `get_balance()` funksiyasi

---

## T-200-007 · Notification Agent — xabar formatlash
**Model:** `claude-sonnet-4-6` | **Tugatildi:** 2026-05-07

- [x] T-200-007-1 · Ertalab eslatma formati (09:00)
- [x] T-200-007-2 · Kechqurun natija formati (23:00) — isimlar ro'yxati + coinlar
- [x] T-200-007-3 · `_send()` — Telegram HTML parse_mode yuborish

---

## T-200-008 · Scheduler — 9:00 va 23:00
**Model:** `claude-sonnet-4-6` | **Tugatildi:** 2026-05-07

- [x] T-200-008-1 · `APScheduler AsyncIOScheduler` sozlash
- [x] T-200-008-2 · `morning_job()` — eslatma barcha faol guruhlarga
- [x] T-200-008-3 · `evening_job()` — scraping → coin → notification
- [x] T-200-008-4 · Timezone: `Asia/Tashkent`

---

## T-200-009 · Main entry point
**Model:** `claude-sonnet-4-6` | **Tugatildi:** 2026-05-07

- [x] T-200-009-1 · Session boshida `session_start_pull()`
- [x] T-200-009-2 · `init_db()` — DB va jadvallar
- [x] T-200-009-3 · Scheduler start
- [x] T-200-009-4 · Telegram bot polling start

---
