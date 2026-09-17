from datetime import datetime, time

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BaselineScheduleEntry(Base):
    __tablename__ = "baseline_schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    subject_code: Mapped[str] = mapped_column(String(20))
    class_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    lab_id: Mapped[int | None] = mapped_column(ForeignKey("labs.id"), nullable=True)
    day_of_week: Mapped[str] = mapped_column(String(10))
    start_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    delivery_weeks: Mapped[list[int]] = mapped_column(JSON)
    session_frequency: Mapped[str] = mapped_column(String(20), default="weekly")
    cohort_size: Mapped[int] = mapped_column(Integer)

    occurrences: Mapped[list["ScheduleOccurrence"]] = relationship(
        back_populates="baseline_entry", cascade="all, delete-orphan"
    )


class ScheduleOccurrence(Base):
    __tablename__ = "schedule_occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baseline_entry_id: Mapped[int] = mapped_column(ForeignKey("baseline_schedule_entries.id"))
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"))
    week_number: Mapped[int] = mapped_column(Integer)
    start_datetime: Mapped[datetime] = mapped_column(DateTime)
    end_datetime: Mapped[datetime] = mapped_column(DateTime)

    baseline_entry: Mapped["BaselineScheduleEntry"] = relationship(back_populates="occurrences")
