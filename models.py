from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    marsit_id: Mapped[str] = mapped_column(String(100), unique=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    students: Mapped[list["Student"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    check_logs: Mapped[list["CheckLog"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    marsit_id: Mapped[str] = mapped_column(String(100), unique=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    coin_balance: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped["Group"] = relationship(back_populates="students")
    transactions: Mapped[list["CoinTransaction"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class CoinTransaction(Base):
    __tablename__ = "coin_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(200))
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="transactions")


class CheckLog(Base):
    __tablename__ = "check_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    checked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    check_type: Mapped[str] = mapped_column(String(20))  # "morning" | "evening"
    results_json: Mapped[str] = mapped_column(Text)
    solved_count: Mapped[int] = mapped_column(Integer, default=0)
    unsolved_count: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped["Group"] = relationship(back_populates="check_logs")
