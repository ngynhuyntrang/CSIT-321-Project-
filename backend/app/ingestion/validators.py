"""FR1 validation: flags missing values, unrecognized room codes and malformed
time blocks before any data is inserted into the baseline schedule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import time

import pandas as pd

MISSING_VALUE = "missing_value"
INVALID_ROOM_CODE = "invalid_room_code"
MALFORMED_TIME_BLOCK = "malformed_time_block"

REQUIRED_FIELDS = [
    "subject_code",
    "room_code",
    "day_of_week",
    "start_time",
    "duration_minutes",
    "delivery_weeks",
    "cohort_size",
]

_VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"]
_MAX_WEEK_NUMBER = 52


@dataclass
class RowError:
    row_number: int
    field: str
    error_type: str
    raw_value: str | None
    message: str


@dataclass
class CleanedRow:
    subject_code: str
    class_type: str | None
    room_code: str
    day_of_week: str
    start_time: time
    duration_minutes: int
    delivery_weeks: list[int]
    session_frequency: str
    cohort_size: int


@dataclass
class RowValidationResult:
    row_number: int
    is_valid: bool
    errors: list[RowError] = field(default_factory=list)
    cleaned: CleanedRow | None = None


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    return bool(isinstance(value, str) and not value.strip())


def _parse_time(raw: str) -> time | None:
    text = raw.strip()
    for fmt in _TIME_FORMATS:
        try:
            from datetime import datetime as _dt

            return _dt.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def parse_week_range(raw: str) -> list[int] | None:
    """Parses strings like "1-5,7,9-12" into a sorted list of unique week numbers.

    Returns None if the string is malformed or contains out-of-range weeks.
    """
    text = raw.strip()
    if not text:
        return None

    weeks: set[int] = set()
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            return None
        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", chunk)
        single_match = re.fullmatch(r"\d+", chunk)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start < 1 or end > _MAX_WEEK_NUMBER or start > end:
                return None
            weeks.update(range(start, end + 1))
        elif single_match:
            week = int(chunk)
            if week < 1 or week > _MAX_WEEK_NUMBER:
                return None
            weeks.add(week)
        else:
            return None

    return sorted(weeks) if weeks else None


def validate_row(row_number: int, row: pd.Series, known_room_codes: set[str]) -> RowValidationResult:
    errors: list[RowError] = []

    def get(field_name: str) -> str | None:
        value = row.get(field_name)
        return None if _is_missing(value) else str(value).strip()

    values = {f: get(f) for f in REQUIRED_FIELDS}
    for field_name in REQUIRED_FIELDS:
        if values[field_name] is None:
            errors.append(
                RowError(
                    row_number=row_number,
                    field=field_name,
                    error_type=MISSING_VALUE,
                    raw_value=None,
                    message=f"Required field '{field_name}' is missing.",
                )
            )

    if errors:
        # Missing required fields make further checks meaningless for this row.
        return RowValidationResult(row_number=row_number, is_valid=False, errors=errors)

    room_code = values["room_code"]
    if room_code not in known_room_codes:
        errors.append(
            RowError(
                row_number=row_number,
                field="room_code",
                error_type=INVALID_ROOM_CODE,
                raw_value=room_code,
                message=f"Room code '{room_code}' is not a recognized lab.",
            )
        )

    day_raw = values["day_of_week"]
    day_key = day_raw[:3].lower() if day_raw else ""
    if day_key not in _VALID_DAYS:
        errors.append(
            RowError(
                row_number=row_number,
                field="day_of_week",
                error_type=MALFORMED_TIME_BLOCK,
                raw_value=day_raw,
                message=f"'{day_raw}' is not a recognized day of week.",
            )
        )

    parsed_time = _parse_time(values["start_time"]) if values["start_time"] else None
    if parsed_time is None:
        errors.append(
            RowError(
                row_number=row_number,
                field="start_time",
                error_type=MALFORMED_TIME_BLOCK,
                raw_value=values["start_time"],
                message=f"'{values['start_time']}' is not a recognized time (expected e.g. 09:00 or 2:00 PM).",
            )
        )

    duration_minutes: int | None = None
    try:
        duration_minutes = int(float(values["duration_minutes"]))
        if duration_minutes <= 0:
            raise ValueError
    except ValueError:
        duration_minutes = None
        errors.append(
            RowError(
                row_number=row_number,
                field="duration_minutes",
                error_type=MALFORMED_TIME_BLOCK,
                raw_value=values["duration_minutes"],
                message=f"'{values['duration_minutes']}' is not a valid positive duration in minutes.",
            )
        )

    delivery_weeks = parse_week_range(values["delivery_weeks"])
    if delivery_weeks is None:
        errors.append(
            RowError(
                row_number=row_number,
                field="delivery_weeks",
                error_type=MALFORMED_TIME_BLOCK,
                raw_value=values["delivery_weeks"],
                message=f"'{values['delivery_weeks']}' is not a valid week range (expected e.g. '1-5,7,9-12').",
            )
        )

    cohort_size: int | None = None
    try:
        cohort_size = int(float(values["cohort_size"]))
        if cohort_size <= 0:
            raise ValueError
    except ValueError:
        cohort_size = None
        errors.append(
            RowError(
                row_number=row_number,
                field="cohort_size",
                error_type=MISSING_VALUE,
                raw_value=values["cohort_size"],
                message=f"'{values['cohort_size']}' is not a valid positive cohort size.",
            )
        )

    if errors:
        return RowValidationResult(row_number=row_number, is_valid=False, errors=errors)

    assert parsed_time is not None
    assert duration_minutes is not None
    assert delivery_weeks is not None
    assert cohort_size is not None

    cleaned = CleanedRow(
        subject_code=values["subject_code"],
        class_type=get("class_type"),
        room_code=room_code,
        day_of_week=day_key,
        start_time=parsed_time,
        duration_minutes=duration_minutes,
        delivery_weeks=delivery_weeks,
        session_frequency=(get("session_frequency") or "weekly").lower(),
        cohort_size=cohort_size,
    )
    return RowValidationResult(row_number=row_number, is_valid=True, cleaned=cleaned)


def validate_rows(df: pd.DataFrame, known_room_codes: set[str]) -> list[RowValidationResult]:
    from app.ingestion.parser import to_row_number

    return [
        validate_row(to_row_number(idx), row, known_room_codes) for idx, row in df.iterrows()
    ]
