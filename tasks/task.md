# JORIY TASKLAR

> Yangi task qo'shilganda shu faylga, bajarilganda `done.md` ga ko'chir.

---

## T-300-011 · Marsit.uz sahifa strukturasini aniqlash va scraper sozlash
**Model:** `claude-opus-4-7`
**Status:** `in_progress`

### Micro-tasklar:
- [x] T-300-011-1 · Login sahifasini ochish, form selectorlarini aniqlash
- [ ] T-300-011-2 · Login qilib dashboard sahifasini ko'rish, guruh elementlarini topish
- [ ] T-300-011-3 · Guruh ichiga kirib "uyga vazifa" bo'limini topish
- [ ] T-300-011-4 · O'quvchilar ro'yxati va completion status selectorlarini aniqlash
- [ ] T-300-011-5 · `scraper_agent.py` ni haqiqiy selectorlar bilan yangilash

### Aniqlangan (2026-05-07):
- Login URL: `https://core.marsit.uz/` (root, email emas — **telefon raqam**)
- Phone selector: `get_by_placeholder("Telefon raqam")` — "+998" pre-filled
- Password selector: `get_by_placeholder("Password")`
- Button: `get_by_role("button", name="Kirish")` — initially disabled
- `config.py`: `MARSIT_EMAIL` → `MARSIT_PHONE` ga o'zgartirildi

### Keyingi qadam:
**Telefon raqam va parolni bering** → T-300-011-2 dan davom etamiz (dashboard + guruhlar)

---

## T-200-010 · Telegram guruh ID larini qo'shish
**Model:** `claude-sonnet-4-6`
**Status:** `pending` — foydalanuvchi guruh ID larini berishi kutilmoqda

### Micro-tasklar:
- [ ] T-200-010-1 · Bot token olish (BotFather dan)
- [ ] T-200-010-2 · Guruh Telegram chat ID larini `.env` ga yozish
- [ ] T-200-010-3 · Marsit guruh ID ↔ Telegram chat ID mapping

### Ma'lumotlar:
- `.env` dagi `TELEGRAM_BOT_TOKEN` bo'sh
- Botni guruhga qo'shib `/setgroup <marsit_id>` buyrug'i bilan bog'lash mumkin
- Bu OXIRGI task — shu tugasa loyiha ishga tayyor

---
