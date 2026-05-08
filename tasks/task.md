# JORIY TASKLAR

> Yangi task qo'shilganda shu faylga, bajarilganda `done.md` ga ko'chir.

---

## T-200-010 · Telegram guruh ID larini qo'shish
**Model:** `claude-sonnet-4-6`
**Status:** `pending` — foydalanuvchi guruh ID larini berishi kutilmoqda

### Micro-tasklar:
- [ ] T-200-010-1 · Bot token olish (BotFather dan)
- [ ] T-200-010-2 · Guruh Telegram chat ID larini `.env` ga yozish
- [ ] T-200-010-3 · Marsit guruh ID ↔ Telegram chat ID mapping (`/setgroup` buyrug'i)

### Ma'lumotlar:
- `.env` dagi `TELEGRAM_BOT_TOKEN` bo'sh
- Botni guruhga qo'shib `/setgroup <marsit_id>` buyrug'i bilan bog'lash mumkin

---

## 🔴 KRITIK BUGLAR

---

## T-200-015 · BUG-001: Har API chaqiruvda yangi httpx.Client yaratiladi
**Model:** `claude-sonnet-4-6`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-200-015-1 · `get_groups(client)` imzosiga `client` parametr qo'shish
- [ ] T-200-015-2 · `get_today_results(client, group_id)` imzosiga `client` parametr qo'shish
- [ ] T-200-015-3 · `scrape_all_groups()` da bitta `_get_authenticated_client()` chaqirib, loop bo'yicha uzatish
- [ ] T-200-015-4 · Eski ichki `_get_authenticated_client()` chaqiruvlarini olib tashlash

### Ma'lumotlar:
- **Fayl:** `agents/api_client.py` — `get_groups()`, `get_today_results()`
- **Muammo:** 8 guruh = 9 ta alohida auth tekshiruvi (rate-limit xavfi)
- **Yechim:** Bitta client yaratib, barcha funksiyalarga parametr sifatida uzatish

---

## T-200-016 · BUG-002: Bir kunda ikki marta ishlasa coinlar ikki marta ayiriladi
**Model:** `claude-sonnet-4-6`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-200-016-1 · `process_results()` boshida bugungi `check_logs` yozuvini tekshirish
- [ ] T-200-016-2 · Yozuv mavjud bo'lsa `logger.warning` + early return qo'shish
- [ ] T-200-016-3 · `database.py` da `check_logs.(group_id + checked_at)` compound index qo'shish
- [ ] T-200-016-4 · `init_db()` ga yangi index qo'shish

### Ma'lumotlar:
- **Fayl:** `agents/coin_agent.py` — `process_results()`
- **Muammo:** `/check` buyrug'i + 23:00 scheduler ikkalasi birgalikda ishlasa → `-40 coin` (o'rniga `-20`)
- **Yechim:** `check_logs` da `group_id` + bugungi sana bo'yicha tekshiruv

---

## T-200-017 · BUG-003: `/check` va `/setgroup` autorizatsiyasiz — har kim ishlatishi mumkin
**Model:** `claude-sonnet-4-6`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-200-017-1 · `config.py` ga `ADMIN_CHAT_IDS: list[str]` qo'shish (`.env` dan parse)
- [ ] T-200-017-2 · `bot/handlers.py` da `admin_only` dekorator yozish
- [ ] T-200-017-3 · `cmd_check()` ga `admin_only` dekorator qo'llash
- [ ] T-200-017-4 · `cmd_set_group()` ga `admin_only` dekorator qo'llash
- [ ] T-200-017-5 · `.env.example` ga `ADMIN_CHAT_IDS=` qo'shish

### Ma'lumotlar:
- **Fayl:** `bot/handlers.py` — `cmd_check()`, `cmd_set_group()`
- **Muammo:** Istalgan Telegram foydalanuvchi coin hisobini ishga tushira oladi
- **Yechim:** `.env` da `ADMIN_CHAT_IDS=123456,789012` — faqat shu chat IDlar uchun ruxsat

---

## 🟠 YUQORI BUGLAR

---

## T-100-018 · BUG-004: Faqat birinchi sahifa guruhlar olinadi (pagination yo'q)
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-018-1 · `get_groups()` response strukturasini logga chiqarish (`total`, `pages` field bormi)
- [ ] T-100-018-2 · Pagination bor bo'lsa `while` loop bilan barcha sahifalarni olish
- [ ] T-100-018-3 · Pagination yo'q bo'lsa — hech narsa o'zgartirmaslik

### Ma'lumotlar:
- **Fayl:** `agents/api_client.py:88`
- **Muammo:** `client.get("/api/v1/groups?page=1")` — faqat page 1, qolganlar o'tkazib yuboriladi

---

## T-100-019 · BUG-005: `day["students_progress"]` KeyError — scraper to'xtaydi
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-019-1 · `day["students_progress"]` → `day.get("students_progress", [])` o'zgartirish
- [ ] T-100-019-2 · `day['course_element']` → `day.get('course_element') or {}` o'zgartirish

### Ma'lumotlar:
- **Fayl:** `agents/api_client.py:118-119`
- **Muammo:** API response o'zgarsa yoki key yo'q bo'lsa — unhandled `KeyError`, butun scraping to'xtaydi

---

## T-100-020 · BUG-006: `asyncio.get_event_loop()` deprecated — Python 3.10+ da xato
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-020-1 · `scheduler.py:34` da `get_event_loop()` → `get_running_loop()` o'zgartirish (1 qator)

### Ma'lumotlar:
- **Fayl:** `scheduler/scheduler.py:34`
- **Muammo:** `asyncio.get_event_loop()` Python 3.10+ da async kontekstda deprecated, 3.12+ da crash

---

## T-100-021 · BUG-007: MongoDB connection timeout sozlanmagan — app hang bo'ladi
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-021-1 · `AsyncIOMotorClient` ga `serverSelectionTimeoutMS=5000` qo'shish
- [ ] T-100-021-2 · `AsyncIOMotorClient` ga `connectTimeoutMS=5000` qo'shish
- [ ] T-100-021-3 · `init_db()` ga `await db.command("ping")` qo'shish (ulanish tekshiruvi)

### Ma'lumotlar:
- **Fayl:** `database.py:10`
- **Muammo:** Timeout yo'q → MongoDB Atlas yetib bo'lmasa app abadiy hang bo'ladi (Render cold start)

---

## T-100-022 · BUG-008: `validate()` localhost MongoDB ni o'tkazib yuboradi
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-022-1 · `validate()` ga `MONGODB_URI == "mongodb://localhost:27017"` tekshiruvi qo'shish
- [ ] T-100-022-2 · Default qiymatda bo'lsa `missing` ga qo'shish

### Ma'lumotlar:
- **Fayl:** `config.py:38-41`
- **Muammo:** Default `"mongodb://localhost:27017"` bo'sh string emas → `validate()` dan o'tib ketadi → Render da runtime xato

---

## 🟡 O'RTA BUGLAR

---

## T-100-023 · BUG-009: `coin_transactions` collectionida index yo'q
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-023-1 · `init_db()` ga `coin_transactions.student_marsit_id` index qo'shish
- [ ] T-100-023-2 · `init_db()` ga `coin_transactions.created_at` index qo'shish
- [ ] T-100-023-3 · `init_db()` ga `check_logs.(group_id, checked_at)` compound index qo'shish

### Ma'lumotlar:
- **Fayl:** `database.py:18-23`
- **Muammo:** Kuniga N ta tranzaksiya — index yo'qda leaderboard va tarix so'rovlari sekin

---

## T-200-024 · BUG-010: Alohida `Bot` singleton — `Application.bot` bilan PTB v20+ ziddiyati
**Model:** `claude-sonnet-4-6`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-200-024-1 · `notification_agent.py` ga `set_bot(bot: Bot) -> None` funksiyasi qo'shish
- [ ] T-200-024-2 · `main.py` da `app` yaratilgandan keyin `notification_agent.set_bot(app.bot)` chaqirish
- [ ] T-200-024-3 · `notification_agent.py` dagi `_bot: Bot | None = None` va `get_bot()` singleton o'chirish

### Ma'lumotlar:
- **Fayl:** `agents/notification_agent.py:11-18`
- **Muammo:** PTB v20+ da `Application` ning o'z `bot` i bor; alohida `Bot()` `initialize()` chaqirilmagan → `send_message` ishlamay qolishi mumkin

---

## T-100-025 · BUG-011: `check_type` "evening" ga hardcode — tarix noto'g'ri
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-025-1 · `process_results()` ga `check_type: str = "evening"` parametr qo'shish
- [ ] T-100-025-2 · `scheduler.py` da `morning_job` — kelgusida `check_type="morning"` uzatish
- [ ] T-100-025-3 · `handlers.py` dagi manual `/check` → `check_type="manual"` uzatish

### Ma'lumotlar:
- **Fayl:** `agents/coin_agent.py:56`
- **Muammo:** `models.py` da `"morning" | "evening"` belgilangan, lekin faqat "evening" yoziladi

---

## 🔵 PAST BUGLAR (tozalash)

---

## T-100-026 · BUG-012: Playwright dan qolgan o'lik config qiymatlari
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-026-1 · `config.py` dan `SCREENSHOT_ON_ERROR` o'chirish
- [ ] T-100-026-2 · `config.py` dan `MARSIT_BASE_URL` o'chirish
- [ ] T-100-026-3 · `config.py` dan `MARSIT_DASHBOARD_URL` o'chirish
- [ ] T-100-026-4 · Bu qiymatlar boshqa fayllarda ishlatilmayotganini `grep` bilan tekshirish

### Ma'lumotlar:
- **Fayl:** `config.py:21,23-24`
- **Muammo:** Playwright (T-300-011 da) olib tashlandi, lekin bu 3 ta config qiymati hali qolgan

---

## T-100-027 · BUG-013: `datetime.utcnow()` deprecated (Python 3.12+)
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-027-1 · `from datetime import timezone` import qo'shish
- [ ] T-100-027-2 · `api_client.py:29` — `datetime.utcnow()` → `datetime.now(timezone.utc)`
- [ ] T-100-027-3 · `api_client.py:39,40` — `datetime.utcnow()` → `datetime.now(timezone.utc)` (2 joy)

### Ma'lumotlar:
- **Fayl:** `agents/api_client.py:29,39,40`
- **Muammo:** Python 3.12 da `DeprecationWarning`, kelajakda `RuntimeError`

---

## T-100-028 · BUG-014: `task_done_push()` da `git add -u` — CLAUDE.md qoidasini buzadi
**Model:** `claude-haiku-4-5-20251001`
**Status:** `pending`

### Micro-tasklar:
- [ ] T-100-028-1 · `task_done_push(task_id, message, files: list[str])` parametr qo'shish
- [ ] T-100-028-2 · `git add -u` o'rniga `files` ro'yxati bo'yicha `git add <file>` chaqirish
- [ ] T-100-028-3 · `files` bo'sh bo'lsa — warning va skip

### Ma'lumotlar:
- **Fayl:** `git_manager.py:38`
- **Muammo:** `git add -u` barcha track qilingan fayllarni qo'shadi — tasodifan keraksiz fayllar commitga tushishi mumkin

---
