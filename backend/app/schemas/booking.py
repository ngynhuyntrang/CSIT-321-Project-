import re
from datetime import date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DayKey = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_SUBJECT_CODE = re.compile(r"^[A-Z]{4}\d{3}$")


def _clean_subject_codes(value: list[str]) -> list[str]:
    codes = [code.strip().upper() for code in value if code.strip()]
    if not codes:
        raise ValueError("At least one subject code is required.")
    bad = [code for code in codes if not _SUBJECT_CODE.match(code)]
    if bad:
        raise ValueError(f"Subject codes look like CSCI235; got {', '.join(bad)}.")
    return list(dict.fromkeys(codes))


class Recurrence(BaseModel):
    """Explicit occurrence dates for a manual booking. Dates are generated
    from a real first date -- never derived from a teaching-week number, which
    has no verified date mapping (docs/architecture.md)."""

    first_date: date
    occurrences: int = Field(ge=1, le=30)
    frequency: Literal["weekly", "fortnightly"] = "weekly"
    skip_dates: list[date] = []

    def dates(self) -> list[date]:
        step = timedelta(days=7 if self.frequency == "weekly" else 14)
        skip = set(self.skip_dates)
        result: list[date] = []
        current = self.first_date
        # Skipped dates don't count towards `occurrences`; cap the walk so a
        # skip list covering every candidate can't loop forever.
        for _ in range(self.occurrences + len(skip)):
            if len(result) == self.occurrences:
                break
            if current not in skip:
                result.append(current)
            current += step
        return result


class BookingSchedule(BaseModel):
    subject_codes: list[str]
    class_type: str = Field(min_length=1, max_length=50)
    lab_id: int
    start_time: time
    duration_minutes: int = Field(ge=15, le=8 * 60)
    cohort_size: int = Field(ge=0, le=1000)

    @field_validator("subject_codes")
    @classmethod
    def codes(cls, value: list[str]) -> list[str]:
        return _clean_subject_codes(value)


class BookingCreate(BookingSchedule):
    activity_name: str | None = Field(default=None, max_length=100)
    week_pattern_raw: str | None = Field(default=None, max_length=200)
    recurrence: Recurrence


class BookingUpdate(BaseModel):
    activity_name: str | None = Field(default=None, max_length=100)
    subject_codes: list[str] | None = None
    class_type: str | None = Field(default=None, min_length=1, max_length=50)
    lab_id: int | None = None
    day_of_week: DayKey | None = None
    start_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=8 * 60)
    cohort_size: int | None = Field(default=None, ge=0, le=1000)
    week_pattern_raw: str | None = Field(default=None, max_length=200)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("subject_codes")
    @classmethod
    def codes(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _clean_subject_codes(value)


class BookingCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class BookingCheckRequest(BookingSchedule):
    """Dry-run input for the live checks panel. For a new booking pass
    `recurrence`; for an edit pass `entry_id` (and `day_of_week` to preview a
    day move) and the booking's existing dates are used."""

    entry_id: int | None = None
    day_of_week: DayKey | None = None
    recurrence: Recurrence | None = None

    @model_validator(mode="after")
    def needs_dates(self) -> "BookingCheckRequest":
        if self.entry_id is None and self.recurrence is None:
            raise ValueError("Provide either entry_id or recurrence.")
        return self


class CheckItem(BaseModel):
    level: Literal["ok", "warning", "error"]
    title: str
    detail: str


class BookingCheckResult(BaseModel):
    can_save: bool
    occurrence_count: int
    first_date: date | None
    last_date: date | None
    checks: list[CheckItem]


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_name: str | None
    subject_codes: list[str]
    class_type: str
    lab_id: int | None
    lab_code: str | None
    lab_capacity: int | None
    day_of_week: str
    start_time: time
    duration_minutes: int
    cohort_size: int
    week_pattern_raw: str | None
    source: str
    status: str
    occurrence_count: int
    first_date: date | None
    last_date: date | None
    has_clash: bool
    over_capacity: bool


class BookingStats(BaseModel):
    total: int
    manual: int
    clashes: int
    over_capacity: int


class BookingList(BaseModel):
    items: list[BookingOut]
    total: int
    page: int
    page_size: int
    stats: BookingStats


class BookingChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    changes: dict
    reason: str | None
    user_name: str | None
    created_at: datetime


class BookingDetail(BookingOut):
    dates: list[date]
    history: list[BookingChangeOut]
