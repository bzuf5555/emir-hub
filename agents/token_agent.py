"""
Token Agent — api_client.py dagi session boshqaruvining thin wrapper.
Tashqi kodga clear_session() ni ta'minlaydi.
"""
from pathlib import Path
from config import config


def clear_session() -> None:
    path = Path(config.SESSION_FILE)
    if path.exists():
        path.unlink()
