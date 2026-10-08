"""FR1 validation against the real UOW Enterprise export format.

Flags missing values, unrecognized room codes and malformed time/duration/date
blocks before any data is inserted into the baseline schedule. Two severities:

- "error": the row is excluded from the baseline (e.g. missing required
  field, unrecognized room, unparseable duration/time/date).
- "warning": the row IS still inserted, but flagged for review (e.g. a
  booking recorded with 0 attendees, or a start/end/duration mismatch).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import pandas as pd

from app.ingestion.parser import parse_module_name

ERROR = "error"
WARNING = "warning"

MISSING_VALUE = "missing_value"
INVALID_ROOM_CODE = "invalid_room_code"
MALFORMED_DAY = "malformed_day"
MALFORMED_TIME = "malformed_time"
MALFORMED_DURATION = "malformed_duration"
MALFORMED_DATE = "malformed_date"
UNPARSEABLE_SUBJECT_CODE = "unparseable_subject_code"
INVALID_COHORT_SIZE = "invalid_cohort_size"
ZERO_COHORT_SIZE = "zero_cohort_size"
DURATION_END_TIME_MISMATCH = "duration_end_time_mismatch"
DATE_COUNT_MISMATCH = "date_count_mismatch"
CAPACITY_MISMATCH = "capacity_mismatch"

REQUIRED_FIELDS = [
    "class_type",
    "module_name_raw",
    "cohort_size",
    "duration_raw",
    "day_of_week",
    "start_time_raw",
    "end_time_raw",
    "room_code",
    "activity_dates_raw",
]

_VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"]


@dataclass
class RowError:
    row_number: int
    field: str
    error_type: str
    severity: str
    raw_value: str | None
    message: str


@dataclass
class CleanedRow:
    activity_name: str | None
    subject_codes: list[str]
    class_type: str
    room_code: str
    day_of_week: str
    start_time: time
    duration_minutes: int
    cohort_size: int
    dates: list[date]
    week_pattern_raw: str | None
    teaching_weeks_count: int | None
    room_capacity: int | None


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
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def _parse_duration_minutes(raw: str) -> int | None:
    """Parses an "HH:MM" elapsed-duration string (e.g. "02:00" = 120 min)."""
    try:
        parsed = datetime.strptime(raw.strip(), "%H:%M")
    except ValueError:
        return None
    return parsed.hour * 60 + parsed.minute


def parse_activity_dates(raw: str) -> list[date] | None:
    """Parses "17/03/2026,24/03/2026,..." (unpadded D/M/YYYY) into dates.

    Returns None if the field is empty or any entry is unparseable.
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return None

    dates: list[date] = []
    for part in parts:
        try:
            dates.append(datetime.strptime(part, "%d/%m/%Y").date())
        except ValueError:
            return None
    return dates


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
                    severity=ERROR,
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
                severity=ERROR,
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
                error_type=MALFORMED_DAY,
                severity=ERROR,
                raw_value=day_raw,
                message=f"'{day_raw}' is not a recognized day of week.",
            )
        )

    start_time = _parse_time(values["start_time_raw"])
    if start_time is None:
        errors.append(
            RowError(
                row_number=row_number,
                field="start_time",
                error_type=MALFORMED_TIME,
                severity=ERROR,
                raw_value=values["start_time_raw"],
                message=(
                    f"'{values['start_time_raw']}' is not a recognized time "
                    "(expected e.g. 09:00 or 2:00 PM)."
                ),
            )
        )

    # End time is only used to cross-check duration, not to build occurrences
    # (start_time + duration is authoritative -- see the mismatch check
    # below), so a malformed end time is a warning, not a blocking error.
    end_time = _parse_time(values["end_time_raw"])
    if end_time is None:
        errors.append(
            RowError(
                row_number=row_number,
                field="end_time",
                error_type=MALFORMED_TIME,
                severity=WARNING,
                raw_value=values["end_time_raw"],
                message=(
                    f"'{values['end_time_raw']}' is not a recognized time; "
                    "could not cross-check against duration."
                ),
            )
        )

    duration_minutes = _parse_duration_minutes(values["duration_raw"])
    if duration_minutes is None:
        errors.append(
            RowError(
                row_number=row_number,
                field="duration_raw",
                error_type=MALFORMED_DURATION,
                severity=ERROR,
                raw_value=values["duration_raw"],
                message=(
                    f"'{values['duration_raw']}' is not a valid HH:MM duration "
                    "(expected e.g. '02:00')."
                ),
            )
        )

    if start_time is not None and end_time is not None and duration_minutes is not None:
        expected_end = (
            datetime.combine(date.min, start_time) + timedelta(minutes=duration_minutes)
        ).time()
        if expected_end != end_time:
            errors.append(
                RowError(
                    row_number=row_number,
                    field="duration_raw",
                    error_type=DURATION_END_TIME_MISMATCH,
                    severity=WARNING,
                    raw_value=values["duration_raw"],
                    message=(
                        f"Start ({start_time}) + duration ({duration_minutes} min) = "
                        f"{expected_end}, which does not match the recorded end time "
                        f"({end_time}). Using start + duration as authoritative."
                    ),
                )
            )

    cohort_size: int | None = None
    try:
        cohort_size = int(float(values["cohort_size"]))
        if cohort_size < 0:
            raise ValueError
    except ValueError:
        cohort_size = None
        errors.append(
            RowError(
                row_number=row_number,
                field="cohort_size",
                error_type=INVALID_COHORT_SIZE,
                severity=ERROR,
                raw_value=values["cohort_size"],
                message=f"'{values['cohort_size']}' is not a valid non-negative cohort size.",
            )
        )
    else:
        if cohort_size == 0:
            errors.append(
                RowError(
                    row_number=row_number,
                    field="cohort_size",
                    error_type=ZERO_COHORT_SIZE,
                    severity=WARNING,
                    raw_value=values["cohort_size"],
                    message=(
                        "Cohort size recorded as 0 -- the room is still booked for this "
                        "time block; verify before treating this as confirmed zero "
                        "attendance."
                    ),
                )
            )

    dates = parse_activity_dates(values["activity_dates_raw"])
    if dates is None:
        errors.append(
            RowError(
                row_number=row_number,
                field="activity_dates_raw",
                error_type=MALFORMED_DATE,
                severity=ERROR,
                raw_value=values["activity_dates_raw"],
                message=(
                    f"'{values['activity_dates_raw']}' is not a valid comma-separated "
                    "list of D/M/YYYY dates."
                ),
            )
        )

    subject_codes = parse_module_name(values["module_name_raw"])
    if not subject_codes:
        errors.append(
            RowError(
                row_number=row_number,
                field="module_name_raw",
                error_type=UNPARSEABLE_SUBJECT_CODE,
                severity=ERROR,
                raw_value=values["module_name_raw"],
                message=f"Could not extract a subject code from '{values['module_name_raw']}'.",
            )
        )

    # Cross-check only -- never used to assign week numbers (see
    # ScheduleOccurrence.week_number). Optional field: absence isn't an error.
    teaching_weeks_count: int | None = None
    teaching_weeks_raw = row.get("teaching_weeks_count_raw")
    if not _is_missing(teaching_weeks_raw):
        try:
            teaching_weeks_count = int(float(str(teaching_weeks_raw).strip()))
        except ValueError:
            teaching_weeks_count = None
    week_pattern_raw = row.get("week_pattern_raw")
    week_pattern_raw = None if _is_missing(week_pattern_raw) else str(week_pattern_raw).strip()

    # Cross-check-only -- not required to ingest a row. Reconciled against
    # Lab.capacity (first value wins; a later conflicting value is flagged as
    # a warning) in app.ingestion.service, since that needs the Lab record,
    # not just this row.
    room_capacity: int | None = None
    room_capacity_raw = row.get("room_capacity_raw")
    if not _is_missing(room_capacity_raw):
        try:
            parsed_capacity = int(float(str(room_capacity_raw).strip()))
            if parsed_capacity >= 0:
                room_capacity = parsed_capacity
        except ValueError:
            room_capacity = None

    if dates is not None and teaching_weeks_count is not None and len(dates) != teaching_weeks_count:
        errors.append(
            RowError(
                row_number=row_number,
                field="activity_dates_raw",
                error_type=DATE_COUNT_MISMATCH,
                severity=WARNING,
                raw_value=values["activity_dates_raw"],
                message=(
                    f"{len(dates)} activity date(s) were listed but 'Number Of Teaching "
                    f"Weeks' says {teaching_weeks_count}. The listed dates are used as-is."
                ),
            )
        )

    if any(e.severity == ERROR for e in errors):
        return RowValidationResult(row_number=row_number, is_valid=False, errors=errors)

    assert start_time is not None
    assert duration_minutes is not None
    assert cohort_size is not None
    assert dates is not None

    cleaned = CleanedRow(
        activity_name=get("activity_name"),
        subject_codes=subject_codes,
        class_type=values["class_type"],
        room_code=room_code,
        day_of_week=day_key,
        start_time=start_time,
        duration_minutes=duration_minutes,
        cohort_size=cohort_size,
        dates=dates,
        week_pattern_raw=week_pattern_raw,
        teaching_weeks_count=teaching_weeks_count,
        room_capacity=room_capacity,
    )
    return RowValidationResult(row_number=row_number, is_valid=True, errors=errors, cleaned=cleaned)


def validate_rows(df: pd.DataFrame, known_room_codes: set[str]) -> list[RowValidationResult]:
    from app.ingestion.parser import to_row_number

    return [
        validate_row(to_row_number(idx), row, known_room_codes) for idx, row in df.iterrows()
    ]
