"""Builders for an active baseline with hand-placed bookings, shared by the
booking and student tests."""

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.db.models.baseline import BaselineScheduleEntry, ScheduleOccurrence
from app.db.models.ingestion import IngestionRun
from app.db.models.lab import Lab

# Tuesday 3 March 2026 and the following weeks.
TUE = date(2026, 3, 3)


def weekly(first: date, count: int) -> list[date]:
    return [first + timedelta(weeks=i) for i in range(count)]


def make_baseline(db: Session) -> IngestionRun:
    run = IngestionRun(filename="test.xlsx", status="completed", is_active_baseline=True)
    db.add(run)
    db.flush()
    return run


def make_lab(db: Session, code: str, capacity: int | None) -> Lab:
    lab = Lab(code=code, room_type="computing", capacity=capacity)
    db.add(lab)
    db.flush()
    return lab


def make_entry(
    db: Session,
    run: IngestionRun,
    lab: Lab,
    *,
    subject: str = "CSCI235",
    name: str | None = None,
    class_type: str = "Computer Lab",
    dates: list[date] | None = None,
    start: time = time(10, 0),
    minutes: int = 60,
    cohort: int = 20,
) -> BaselineScheduleEntry:
    dates = dates or weekly(TUE, 4)
    entry = BaselineScheduleEntry(
        ingestion_run_id=run.id,
        activity_name=name or f"{subject}-{class_type[:2].upper()}",
        subject_codes=[subject],
        class_type=class_type,
        lab_id=lab.id,
        day_of_week=["mon", "tue", "wed", "thu", "fri", "sat", "sun"][dates[0].weekday()],
        start_time=start,
        duration_minutes=minutes,
        cohort_size=cohort,
    )
    db.add(entry)
    db.flush()
    for d in dates:
        begin = datetime.combine(d, start)
        db.add(
            ScheduleOccurrence(
                baseline_entry_id=entry.id,
                lab_id=lab.id,
                start_datetime=begin,
                end_datetime=begin + timedelta(minutes=minutes),
            )
        )
    db.commit()
    return entry
