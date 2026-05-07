import subprocess
import logging

logger = logging.getLogger("git_manager")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def session_start_pull() -> None:
    """Session boshida chaqiriladi — o'zgarish bo'lsa pull qiladi."""
    code, out, _ = _run(["git", "status", "--porcelain"])
    if code != 0:
        logger.warning("Git repo topilmadi, skip")
        return

    logger.info("Git status tekshirilmoqda...")

    code, out, err = _run(["git", "pull", "--rebase"])
    if code == 0:
        logger.info(f"Git pull OK: {out or 'already up to date'}")
    else:
        logger.error(f"Git pull xato: {err}")
        _handle_conflict()


def _handle_conflict() -> None:
    code, out, _ = _run(["git", "rebase", "--abort"])
    if code == 0:
        logger.warning("Rebase abort qilindi, merge strategiyasi sinab ko'rilmoqda")
        _run(["git", "pull", "--no-rebase"])


def task_done_push(task_id: str, message: str) -> None:
    """Task tugaganda chaqiriladi — commit va push."""
    _run(["git", "add", "-u"])

    code, _, err = _run(["git", "commit", "-m", f"task({task_id}): {message}"])
    if code != 0:
        if "nothing to commit" in err:
            logger.info("Commit qilgulik o'zgarish yo'q")
            return
        logger.error(f"Commit xato: {err}")
        return

    code, out, err = _run(["git", "push"])
    if code == 0:
        logger.info(f"Push OK: {out}")
    else:
        logger.error(f"Push xato: {err}")
