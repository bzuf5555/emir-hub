import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MARSIT_PHONE: str = os.getenv("MARSIT_PHONE", "")
    MARSIT_PASSWORD: str = os.getenv("MARSIT_PASSWORD", "")

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    MENTOR_CHAT_ID: str = os.getenv("MENTOR_CHAT_ID", "")

    # BUG-003: admin chat IDlar — vergul bilan ajratilgan
    ADMIN_CHAT_IDS: list[str] = [
        x.strip() for x in os.getenv("ADMIN_CHAT_IDS", "").split(",") if x.strip()
    ]

    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "emir_hub")

    CHECK_TIME_MORNING: str = os.getenv("CHECK_TIME_MORNING", "09:00")
    CHECK_TIME_EVENING: str = os.getenv("CHECK_TIME_EVENING", "23:00")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tashkent")

    # BUG-012: Playwright dan qolgan o'lik qiymatlar olib tashlandi
    # (SCREENSHOT_ON_ERROR, MARSIT_BASE_URL, MARSIT_DASHBOARD_URL)

    SESSION_FILE: str = "session/cookies.json"
    SESSION_EXPIRY_HOURS: int = 12

    COIN_SOLVED: int = 5
    COIN_UNSOLVED: int = -20

    def validate(self) -> None:
        _MONGO_DEFAULT = "mongodb://localhost:27017"
        required = {
            "MARSIT_PHONE": self.MARSIT_PHONE,
            "MARSIT_PASSWORD": self.MARSIT_PASSWORD,
            "TELEGRAM_BOT_TOKEN": self.TELEGRAM_BOT_TOKEN,
            # BUG-022: default localhost ham missing hisoblanadi
            "MONGODB_URI": "" if self.MONGODB_URI == _MONGO_DEFAULT else self.MONGODB_URI,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f".env da yetishmayapti: {', '.join(missing)}")


config = Config()
