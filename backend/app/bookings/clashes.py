"""Room double-booking and cohort-overlap detection over the active baseline.

Overlap rule (docs/architecture.md): two intervals overlap only if
`a.start < b.end AND b.start < a.end`. Back-to-back bookings (09:00-10:00 and
10:00-11:00) touch at a point and are not a clash.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Query, Session

from app.db.models.baseline import BaselineScheduleEntry, ScheduleOccurrence
from app.db.models.ingestion import IngestionRun

Interval = tuple[datetime, datetime]


def overlaps(a: Interval, b: Interval) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def active_entries(db: Session) -> Query[BaselineScheduleEntry]:
    """Bookings that currently take up room time: rows of the active baseline
    run that haven't been cancelled."""
    return (
        db.query(BaselineScheduleEntry)
        .join(IngestionRun, BaselineScheduleEntry.ingestion_run_id == IngestionRun.id)
        .filter(IngestionRun.is_active_baseline.is_(True))
        .filter(BaselineScheduleEntry.status == "active")
    )


def active_baseline_run(db: Session) -> IngestionRun | None:
    return db.query(IngestionRun).filter(IngestionRun.is_active_baseline.is_(True)).first()


@dataclass
class Clash:
    entry_id: int
    activity_name: str | None
    class_type: str
    subject_codes: list[str]
    start: datetime
    end: datetime


def _occurrences_for(
    db: Session, intervals: list[Interval], exclude_entry_id: int | None, lab_id: int | None
) -> list[tuple[ScheduleOccurrence, BaselineScheduleEntry]]:
    if not intervals:
        return []
    window_start = min(start for start, _ in intervals)
    window_end = max(end for _, end in intervals)
    active_ids = active_entries(db).with_entities(BaselineScheduleEntry.id).scalar_subquery()
    query = (
        db.query(ScheduleOccurrence, BaselineScheduleEntry)
        .join(BaselineScheduleEntry, ScheduleOccurrence.baseline_entry_id == BaselineScheduleEntry.id)
        .filter(ScheduleOccurrence.baseline_entry_id.in_(active_ids))
        .filter(ScheduleOccurrence.start_datetime < window_end)
        .filter(ScheduleOccurrence.end_datetime > window_start)
    )
    if lab_id is not None:
        query = query.filter(ScheduleOccurrence.lab_id == lab_id)
    if exclude_entry_id is not None:
        query = query.filter(ScheduleOccurrence.baseline_entry_id != exclude_entry_id)
    return query.all()


def _collect(
    rows: list[tuple[ScheduleOccurrence, BaselineScheduleEntry]],
    intervals: list[Interval],
    keep: Callable[[BaselineScheduleEntry], bool] = lambda _entry: True,
) -> list[Clash]:
    clashes: list[Clash] = []
    for occ, entry in rows:
        if not keep(entry):
            continue
        if any(overlaps((occ.start_datetime, occ.end_datetime), iv) for iv in intervals):
            clashes.append(
                Clash(
                    entry_id=entry.id,
                    activity_name=entry.activity_name,
                    class_type=entry.class_type,
                    subject_codes=list(entry.subject_codes),
                    start=occ.start_datetime,
                    end=occ.end_datetime,
                )
            )
    clashes.sort(key=lambda c: c.start)
    return clashes


def find_clashes(
    db: Session, lab_id: int, intervals: list[Interval], exclude_entry_id: int | None = None
) -> list[Clash]:
    """Occurrences of other active bookings in `lab_id` that overlap `intervals`."""
    rows = _occurrences_for(db, intervals, exclude_entry_id, lab_id)
    return _collect(rows, intervals)


def cohort_overlaps(
    db: Session,
    subject_codes: list[str],
    class_type: str,
    intervals: list[Interval],
    exclude_entry_id: int | None = None,
) -> list[Clash]:
    """Other active bookings for the same subject, of a *different* class type,
    that overlap in time (in any room). Students take one class of each type,
    so e.g. a lab overlapping that subject's tutorial is a likely timetable
    conflict for the cohort; two lab groups overlapping is not."""
    codes = set(subject_codes)
    rows = _occurrences_for(db, intervals, exclude_entry_id, None)
    return _collect(
        rows,
        intervals,
        keep=lambda entry: entry.class_type != class_type and bool(codes & set(entry.subject_codes)),
    )


def all_clashing_entry_ids(db: Session) -> set[int]:
    """Every active booking that overlaps another active booking in the same
    room, via a per-room sweep over all occurrences."""
    active_ids = active_entries(db).with_entities(BaselineScheduleEntry.id).scalar_subquery()
    rows = (
        db.query(
            ScheduleOccurrence.lab_id,
            ScheduleOccurrence.start_datetime,
            ScheduleOccurrence.end_datetime,
            ScheduleOccurrence.baseline_entry_id,
        )
        .filter(ScheduleOccurrence.baseline_entry_id.in_(active_ids))
        .all()
    )
    by_lab: dict[int, list[tuple[datetime, datetime, int]]] = defaultdict(list)
    for lab_id, start, end, entry_id in rows:
        by_lab[lab_id].append((start, end, entry_id))

    clashing: set[int] = set()
    for occurrences in by_lab.values():
        occurrences.sort()
        open_: list[tuple[datetime, int]] = []  # (end, entry_id) still running
        for start, end, entry_id in occurrences:
            open_ = [(e, eid) for e, eid in open_ if e > start]
            for _, other_id in open_:
                if other_id != entry_id:
                    clashing.update((entry_id, other_id))
            open_.append((end, entry_id))
    return clashing
