from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentSubject(Base):
    """A subject a student says they're enrolled in. The Enterprise export has
    no per-student enrolment data, so students add their own subjects."""

    __tablename__ = "student_subjects"
    __table_args__ = (UniqueConstraint("user_id", "subject_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject_code: Mapped[str] = mapped_column(String(20))


class ClassSelection(Base):
    """A student's chosen class (one per subject, class type and teaching
    period). Seats left = room capacity - export cohort size - selections."""

    __tablename__ = "class_selections"
    __table_args__ = (UniqueConstraint("user_id", "entry_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("baseline_schedule_entries.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class Feedback(Base):
    """Student feedback on lab scheduling. `anonymous` hides the author from
    staff views; the link is still stored so abuse can be followed up."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("baseline_schedule_entries.id"), nullable=True
    )
    lab_id: Mapped[int | None] = mapped_column(ForeignKey("labs.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(10))
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(String(2000))
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(10), default="received")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
