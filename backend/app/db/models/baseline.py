from datetime import UTC, datetime, time

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BaselineScheduleEntry(Base):
    """One row of the ingested timetable, after validation/cleaning.

    `subject_codes` is a list because some real Enterprise rows jointly serve
    multiple subjects (e.g. an undergrad/postgrad pairing sharing one class).
    `week_pattern_raw` / `teaching_weeks_count` are kept only as the original
    file's reference text -- they are never parsed into `ScheduleOccurrence`
    week numbers (see `ScheduleOccurrence.week_number`).

    `source` is "enterprise" for rows from an export and "manual" for
    bookings an admin created in the app. A cancelled booking keeps its row
    (with `status="cancelled"`) for the audit trail, but its occurrences are
    deleted so it no longer takes up room time.
    """

    __tablename__ = "baseline_schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    activity_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject_codes: Mapped[list[str]] = mapped_column(JSON)
    class_type: Mapped[str] = mapped_column(String(50))
    lab_id: Mapped[int | None] = mapped_column(ForeignKey("labs.id"), nullable=True)
    day_of_week: Mapped[str] = mapped_column(String(10))
    start_time: Mapped[time] = mapped_column(Time)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    cohort_size: Mapped[int] = mapped_column(Integer)
    week_pattern_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)
    teaching_weeks_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="enterprise", server_default="enterprise")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(UTC)
    )

    occurrences: Mapped[list["ScheduleOccurrence"]] = relationship(
        back_populates="baseline_entry", cascade="all, delete-orphan"
    )


class ScheduleOccurrence(Base):
    """A single concrete calendar occurrence, built directly from the
    export's "Activity Dates (Individual)" column -- not derived from a week
    number + weekday + assumed semester start.

    `week_number` is always null until a verified date-to-teaching-week
    reference (e.g. an official UOW semester calendar) is introduced; pairing
    dates to `Teaching Week Pattern` positionally would be an unverified
    guess, not a fact (see docs/architecture.md).
    """

    __tablename__ = "schedule_occurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baseline_entry_id: Mapped[int] = mapped_column(ForeignKey("baseline_schedule_entries.id"))
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id"))
    week_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_datetime: Mapped[datetime] = mapped_column(DateTime)
    end_datetime: Mapped[datetime] = mapped_column(DateTime)

    baseline_entry: Mapped["BaselineScheduleEntry"] = relationship(back_populates="occurrences")
