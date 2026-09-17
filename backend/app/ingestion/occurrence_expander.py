"""Expands a validated baseline schedule row into concrete per-occurrence
(lab, start_datetime, end_datetime) rows, directly from the export's own
"Activity Dates (Individual)" list.

This deliberately does not derive dates from a week number + weekday +
assumed semester start: the export already gives exact calendar dates, and
those are ground truth. `week_number` is always None here -- see
`ScheduleOccurrence.week_number` for why.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass
class Occurrence:
    lab_id: int
    week_number: int | None
    start_datetime: datetime
    end_datetime: datetime


def expand_occurrences(
    *,
    lab_id: int,
    dates: list[date],
    start_time: time,
    duration_minutes: int,
) -> list[Occurrence]:
    """Generates one Occurrence per date in `dates`."""
    occurrences: list[Occurrence] = []
    for occurrence_date in dates:
        start_dt = datetime.combine(occurrence_date, start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        occurrences.append(
            Occurrence(lab_id=lab_id, week_number=None, start_datetime=start_dt, end_datetime=end_dt)
        )
    return occurrences
