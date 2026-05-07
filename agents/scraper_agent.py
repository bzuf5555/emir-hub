"""
Scraper Agent — marsit.uz API orqali ma'lumot oladi.
Playwright ishlatilmaydi. api_client.py orqali to'g'ridan-to'g'ri REST.

Oqim:
  1. get_groups() → guruhlar ro'yxati
  2. Har guruh uchun get_today_results(group_id) → bugungi is_completed statusi
  3. GroupData ro'yxati qaytariladi
"""
import logging
from dataclasses import dataclass, field

from agents.api_client import get_groups, get_today_results

logger = logging.getLogger("scraper_agent")


@dataclass
class StudentResult:
    marsit_id: str
    name: str
    solved: bool
    score: float = 0.0


@dataclass
class GroupData:
    marsit_id: str
    name: str
    students: list[StudentResult] = field(default_factory=list)
    has_lesson_today: bool = False


def scrape_all_groups() -> list[GroupData]:
    """Barcha guruhlarning bugungi vazifa natijasini qaytaradi."""
    raw_groups = get_groups()
    result: list[GroupData] = []

    for g in raw_groups:
        group_id = g["id"]
        group_name = g.get("name", f"Guruh {group_id}")

        today_progress = get_today_results(group_id)

        students = [
            StudentResult(
                marsit_id=str(s["student_id"]),
                name=s["student_name"],
                solved=bool(s.get("is_completed", False)),
                score=float(s.get("score", 0.0)),
            )
            for s in today_progress
        ]

        result.append(GroupData(
            marsit_id=str(group_id),
            name=group_name,
            students=students,
            has_lesson_today=len(today_progress) > 0,
        ))
        logger.info(
            f"{group_name}: {sum(1 for s in students if s.solved)}/{len(students)} ta bajarildi"
        )

    return result
