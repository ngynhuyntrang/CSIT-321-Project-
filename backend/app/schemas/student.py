from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field


class PeriodOut(BaseModel):
    id: str
    start: date
    end: date


class ClassOption(BaseModel):
    entry_id: int
    activity_name: str | None
    class_type: str
    day_of_week: str
    start_time: time
    duration_minutes: int
    lab_code: str | None
    capacity: int | None
    cohort_size: int
    picks: int
    seats_left: int | None
    full: bool
    selected: bool
    clashes_with: list[str]
    adds_day: bool
    days_after: int
    first_date: date
    last_date: date
    occurrence_count: int


class ClassGroup(BaseModel):
    class_type: str
    options: list[ClassOption]


class SubjectClasses(BaseModel):
    subject_code: str
    groups: list[ClassGroup]


class ClassOptionsOut(BaseModel):
    period: PeriodOut | None
    periods: list[PeriodOut]
    subjects: list[SubjectClasses]
    on_campus_days: list[str]


class AddSubject(BaseModel):
    subject_code: str = Field(min_length=3, max_length=20)
    period_id: str | None = None


class SelectClass(BaseModel):
    entry_id: int


class TimetableEvent(BaseModel):
    entry_id: int
    subject_codes: list[str]
    activity_name: str | None
    class_type: str
    lab_code: str | None
    start: datetime
    end: datetime
    day_of_week: str


class TimetableOut(BaseModel):
    week_start: date
    weeks: list[date]
    events: list[TimetableEvent]
    on_campus_days: list[str]
    next_class: TimetableEvent | None
    selected_count: int


class RoomAvailability(BaseModel):
    lab_id: int
    lab_code: str
    capacity: int | None
    free_minutes: dict[str, int]


class FreeNow(BaseModel):
    lab_code: str
    capacity: int | None
    free: bool
    until: datetime


class AvailabilityOut(BaseModel):
    week_start: date
    day_start: str
    day_end: str
    has_bookings: bool
    rooms: list[RoomAvailability]
    now: datetime
    free_now: list[FreeNow] | None


class FeedbackCreate(BaseModel):
    entry_id: int | None = None
    lab_id: int | None = None
    category: Literal["timing", "room", "days", "other"]
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=3, max_length=2000)
    anonymous: bool = False


class FeedbackOut(BaseModel):
    id: int
    entry_id: int | None
    class_label: str | None
    lab_code: str | None
    category: str
    rating: int
    comment: str
    anonymous: bool
    status: str
    author: str | None
    created_at: datetime


class FeedbackUpdate(BaseModel):
    status: Literal["received", "reviewed"]
