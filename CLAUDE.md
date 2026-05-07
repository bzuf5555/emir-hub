# EMIR-HUB — CLAUDE QOIDALARI (QATIY)

## 1. SESSION BOSHLANGANDA (HAR DOIM)

```bash
git status
# O'zgarish bo'lsa:
git pull --rebase
# Conflict bo'lsa: git status → diff tahlil → resolve → git add → git rebase --continue
```

## 2. TASK TUGAGANDA (HAR DOIM)

```bash
git add <faqat_o'zgargan_fayllar>
git commit -m "task(T-XXX): <nima qilindi>"
git push
```

## 3. TASK TIZIMI

Har bir task quyidagi formatda bo'lishi SHART:

```json
{
  "id": "T-200-001",
  "title": "Scraper login qismi",
  "model": "claude-sonnet-4-6",
  "complexity": 200,
  "status": "pending | in_progress | done | blocked",
  "micro_tasks": [
    { "id": "T-200-001-1", "title": "Login form topish", "done": false },
    { "id": "T-200-001-2", "title": "Credentials kiritish", "done": false }
  ],
  "data": {
    "url": "https://core.marsit.uz/teacher-dashboard",
    "selector": "#login-form"
  }
}
```

**Har yangi task yaratilganda micro-tasklarga bo'linishi SHART.**

## 4. MODEL TANLASH QOIDASI

| Complexity | Model | Qachon ishlatiladi |
|---|---|---|
| `T-100` | `claude-haiku-4-5-20251001` | Config, format, rename, simple edit |
| `T-200` | `claude-sonnet-4-6` | Feature, bug fix, API integration, scraping |
| `T-300` | `claude-opus-4-7` | Architecture, complex logic, system design |

**Qoida:** Shubha bo'lsa — pastroq model. Opus faqat haqiqatan murakkab ishlarda.

## 5. TOKEN / SESSION AGENTI (QATIY)

- Session cookies `session/cookies.json` da saqlanadi
- Login qilishdan OLDIN cookies yuklanadi
- Cookies eskirgan bo'lsa → qayta login → yangi cookies saqlash
- Session agenti boshqa agentlardan MUSTAQIL ishlaydi
- `session/` papkasi `.gitignore` da bo'lishi SHART

## 6. KOD SIFATI QOIDALARI

- **Maximal fayl uzunligi:** 300 qator
- **Type hints:** Pythonda barcha funksiyalarda SHART
- **Hardcoded credentials:** YO'Q — faqat `.env`
- **Izohlar:** Faqat "NIMA UCHUN" aniq bo'lmagan joylarda
- **Funksiya:** Bitta vazifa — bitta funksiya
- **Import:** Absolute import, relative emas

## 7. AGENT QOIDALARI

Loyihada 4 ta asosiy agent:

| Agent | Fayl | Vazifa |
|---|---|---|
| TokenAgent | `agents/token_agent.py` | Session saqlash/yuklash |
| ScraperAgent | `agents/scraper_agent.py` | marsit.uz scraping |
| CoinAgent | `agents/coin_agent.py` | Coin hisob-kitobi |
| NotificationAgent | `agents/notification_agent.py` | Telegram xabar formatlash |

Agentlar `async/await` bilan ishlaydi. Har agent o'z log yozadi.

## 8. MUHIT O'ZGARUVCHILARI

Barcha secrets `.env` da:

```
MARSIT_EMAIL=...
MARSIT_PASSWORD=...
TELEGRAM_BOT_TOKEN=...
DATABASE_URL=sqlite:///emir_hub.db
CHECK_TIME_MORNING=09:00
CHECK_TIME_EVENING=23:00
TIMEZONE=Asia/Tashkent
```

`.env` hech qachon `git add` qilinmaydi.

## 9. LOG QOIDALARI

- Har agent o'z log faylini `logs/` da yuritadi
- Log formati: `[2026-05-07 23:00:01] [AGENT] [LEVEL] Xabar`
- Level: `INFO`, `WARNING`, `ERROR`
- Error bo'lsa — dastur to'xtamaydi, log yoziladi, davom etadi

## 10. GIT COMMIT FORMATI

```
task(T-200-001): login agentini qo'shish
feat(scraper): group list scraping
fix(coins): manfiy coin bug tuzatish
chore(deps): requirements.txt yangilash
```

## 11. TAQIQLANGAN NARSALAR

- `print()` ishlatish (o'rniga `logger.info()`)
- `time.sleep()` > 2 sekund (o'rniga `asyncio.sleep()`)
- Hardcoded URL, parol, token
- `except: pass` yoki `except Exception: pass`
- `git add .` (faqat o'zgargan fayllarni add qilish)
- Fayl ustiga yozish (avval `Read`, keyin `Edit`)

## 12. LOYIHA STRUKTURASI

```
emir-hub/
├── CLAUDE.md               # Shu fayl — qoidalar
├── .env                    # Secrets (gitignore)
├── .env.example            # Template
├── .gitignore
├── requirements.txt
├── main.py                 # Entry point
├── config.py               # Config loader
├── database.py             # DB setup
├── models.py               # SQLAlchemy models
├── git_manager.py          # Git operations
├── agents/
│   ├── token_agent.py
│   ├── scraper_agent.py
│   ├── coin_agent.py
│   └── notification_agent.py
├── bot/
│   ├── bot.py
│   └── handlers.py
├── scheduler/
│   └── scheduler.py
├── session/                # (gitignore)
│   └── cookies.json
├── logs/                   # (gitignore)
└── tasks/
    ├── tasks.json          # Task registry
    └── active.json         # Joriy aktiv tasklar
```
