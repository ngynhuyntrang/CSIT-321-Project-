"""Expands a recurring baseline schedule entry into concrete per-week
occurrences (lab, week_number, start_datetime, end_datetime).

Every downstream feature (utilisation math, double-booking checks, clash
diagnostics) operates on these flat occurrences rather than re-deriving
weekly/fortnightly recurrence logic each time -- this is the single
structural decision that keeps that logic correct in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

_WEEKDAY_INDEX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass
class Occurrence:
    lab_id: int
    week_number: int
    start_datetime: datetime
    end_datetime: datetime


def expand_occurrences(
    *,
    lab_id: int,
    day_of_week: str,
    start_time: time,
    duration_minutes: int,
    delivery_weeks: list[int],
    semester_week1_monday: date,
) -> list[Occurrence]:
    """Generates one Occurrence per entry in delivery_weeks.

    `semester_week1_monday` is the Monday of teaching week 1 for the
    semester this baseline belongs to.
    """
    weekday_offset = _WEEKDAY_INDEX[day_of_week.lower()]
    occurrences: list[Occurrence] = []
    for week_number in delivery_weeks:
        session_date = semester_week1_monday + timedelta(
            weeks=week_number - 1, days=weekday_offset
        )
        start_dt = datetime.combine(session_date, start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        occurrences.append(
            Occurrence(
                lab_id=lab_id,
                week_number=week_number,
                start_datetime=start_dt,
                end_datetime=end_dt,
            )
        )
    return occurrences
