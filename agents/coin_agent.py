import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import Student, CoinTransaction, Group

logger = logging.getLogger("coin_agent")


async def process_results(
    session: AsyncSession,
    group_marsit_id: str,
    student_results: list[dict],
) -> dict:
    """
    student_results: [{"marsit_id": str, "name": str, "solved": bool}, ...]
    Qaytaradi: {"solved": [...Student], "unsolved": [...Student], "total_given": int, "total_taken": int}
    """
    group = await _get_or_create_group(session, group_marsit_id)

    solved_students = []
    unsolved_students = []
    total_given = 0
    total_taken = 0

    for sr in student_results:
        student = await _get_or_create_student(session, sr["marsit_id"], sr["name"], group.id)

        if sr["solved"]:
            student.coin_balance += config.COIN_SOLVED
            total_given += config.COIN_SOLVED
            session.add(CoinTransaction(
                student_id=student.id,
                amount=config.COIN_SOLVED,
                reason=f"Vazifa bajarildi ({date.today()})",
            ))
            solved_students.append(student)
            logger.info(f"{student.name}: +{config.COIN_SOLVED} coin")
        else:
            student.coin_balance += config.COIN_UNSOLVED
            total_taken += abs(config.COIN_UNSOLVED)
            session.add(CoinTransaction(
                student_id=student.id,
                amount=config.COIN_UNSOLVED,
                reason=f"Vazifa bajarilmadi ({date.today()})",
            ))
            unsolved_students.append(student)
            logger.info(f"{student.name}: {config.COIN_UNSOLVED} coin")

    await session.commit()
    return {
        "solved": solved_students,
        "unsolved": unsolved_students,
        "total_given": total_given,
        "total_taken": total_taken,
        "group": group,
    }


async def get_balance(session: AsyncSession, student_marsit_id: str) -> int:
    result = await session.execute(
        select(Student).where(Student.marsit_id == student_marsit_id)
    )
    student = result.scalar_one_or_none()
    return student.coin_balance if student else 0


async def _get_or_create_group(session: AsyncSession, marsit_id: str) -> Group:
    result = await session.execute(select(Group).where(Group.marsit_id == marsit_id))
    group = result.scalar_one_or_none()
    if not group:
        group = Group(marsit_id=marsit_id, name=f"Guruh {marsit_id}")
        session.add(group)
        await session.flush()
    return group


async def _get_or_create_student(
    session: AsyncSession, marsit_id: str, name: str, group_id: int
) -> Student:
    result = await session.execute(select(Student).where(Student.marsit_id == marsit_id))
    student = result.scalar_one_or_none()
    if not student:
        student = Student(marsit_id=marsit_id, name=name, group_id=group_id)
        session.add(student)
        await session.flush()
    else:
        student.name = name
    return student
