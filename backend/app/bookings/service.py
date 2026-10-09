"""Admin booking management on the active baseline (prototype screens 7-9).

Every write re-runs the room clash check and refuses to save a
double-booking (A2 NFR: zero double-bookings, explicit clash messages).
Capacity and cohort overlaps are soft constraints and only warn.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import String, case, cast, func
from sqlalchemy.orm import Session

from app.bookings.clashes import (
    Clash,
    active_baseline_run,
    active_entries,
    all_clashing_entry_ids,
    cohort_overlaps,
    find_clashes,
)
from app.db.models.baseline import BaselineScheduleEntry, ScheduleOccurrence
from app.db.models.booking import BookingChange
from app.db.models.lab import Lab
from app.db.models.user import User
from app.ingestion.occurrence_expander import expand_occurrences
from app.schemas.booking import (
    BookingCheckRequest,
    BookingCheckResult,
    BookingCreate,
    BookingUpdate,
    CheckItem,
)

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = {
    "mon": "Mon",
    "tue": "Tue",
    "wed": "Wed",
    "thu": "Thu",
    "fri": "Fri",
    "sat": "Sat",
    "sun": "Sun",
}


class BookingError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def format_time(value: time | datetime) -> str:
    hour = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{hour}:{value.minute:02d} {suffix}"


def _end_time(start: time, duration_minutes: int) -> time:
    return (datetime.combine(date.min, start) + timedelta(minutes=duration_minutes)).time()


def slot_label(day: str, start: time, duration_minutes: int) -> str:
    end = _end_time(start, duration_minutes)
    return f"{DAY_NAMES[day]} {format_time(start)}–{format_time(end)}"


def intervals_for(
    dates: list[date], start: time, duration_minutes: int
) -> list[tuple[datetime, datetime]]:
    length = timedelta(minutes=duration_minutes)
    return [(datetime.combine(d, start), datetime.combine(d, start) + length) for d in dates]


def entry_dates(entry: BaselineScheduleEntry) -> list[date]:
    return sorted({occ.start_datetime.date() for occ in entry.occurrences})


def _shift_dates(dates: list[date], from_day: str, to_day: str) -> list[date]:
    delta = DAY_KEYS.index(to_day) - DAY_KEYS.index(from_day)
    return [d + timedelta(days=delta) for d in dates]


def _get_lab(db: Session, lab_id: int) -> Lab:
    lab = db.get(Lab, lab_id)
    if lab is None or not lab.active:
        raise BookingError(404, "Room not found.")
    return lab


def _get_active_entry(db: Session, entry_id: int) -> BaselineScheduleEntry:
    entry = active_entries(db).filter(BaselineScheduleEntry.id == entry_id).first()
    if entry is None:
        exists = db.get(BaselineScheduleEntry, entry_id)
        if exists is not None and exists.status == "cancelled":
            raise BookingError(409, "This booking has been cancelled.")
        raise BookingError(404, "Booking not found in the current baseline.")
    return entry


def _describe(clash: Clash) -> str:
    name = clash.activity_name or "/".join(clash.subject_codes)
    return f"{name} ({clash.class_type})"


def _capacity_check(lab: Lab, cohort_size: int) -> CheckItem:
    if lab.capacity is None:
        return CheckItem(
            level="warning",
            title="Capacity unknown",
            detail=f"{lab.code} has no recorded capacity yet, so room fit can't be checked.",
        )
    if cohort_size > lab.capacity:
        return CheckItem(
            level="warning",
            title="Over capacity",
            detail=f"{cohort_size} students / {lab.capacity} seats in {lab.code}.",
        )
    if cohort_size == lab.capacity:
        return CheckItem(
            level="warning",
            title="At capacity",
            detail=f"{cohort_size} students / {lab.capacity} seats — no spare seats.",
        )
    pct = round(cohort_size / lab.capacity * 100) if lab.capacity else 0
    return CheckItem(
        level="ok",
        title="Fits room capacity",
        detail=f"{cohort_size} students / {lab.capacity} seats ({pct}%).",
    )


def run_checks(
    db: Session,
    *,
    lab: Lab,
    dates: list[date],
    start: time,
    duration_minutes: int,
    cohort_size: int,
    subject_codes: list[str],
    class_type: str,
    exclude_entry_id: int | None,
) -> list[CheckItem]:
    if not dates:
        return [CheckItem(level="error", title="No dates", detail="The booking has no dates.")]
    intervals = intervals_for(dates, start, duration_minutes)
    slot = slot_label(DAY_KEYS[dates[0].weekday()], start, duration_minutes)
    checks: list[CheckItem] = []

    clashes = find_clashes(db, lab.id, intervals, exclude_entry_id)
    if clashes:
        holders = sorted({_describe(c) for c in clashes})
        clash_dates = sorted({c.start.date() for c in clashes})
        checks.append(
            CheckItem(
                level="error",
                title="Double-booking",
                detail=(
                    f"{lab.code} {slot} is held by {', '.join(holders)} on "
                    f"{len(clash_dates)} of {len(dates)} date(s), first on "
                    f"{clash_dates[0]:%d/%m/%Y}. Pick another room or time — "
                    "double-bookings can't be saved."
                ),
            )
        )
    else:
        checks.append(
            CheckItem(
                level="ok",
                title="No room clash",
                detail=f"{lab.code} is free {slot} on all {len(dates)} date(s).",
            )
        )

    checks.append(_capacity_check(lab, cohort_size))

    seen: set[int] = set()
    for clash in cohort_overlaps(db, subject_codes, class_type, intervals, exclude_entry_id):
        if clash.entry_id in seen:
            continue
        seen.add(clash.entry_id)
        minutes = int((clash.end - clash.start).total_seconds() // 60)
        other_slot = slot_label(DAY_KEYS[clash.start.weekday()], clash.start.time(), minutes)
        checks.append(
            CheckItem(
                level="warning",
                title="Cohort overlap",
                detail=(
                    f"{'/'.join(clash.subject_codes)} students also have "
                    f"{_describe(clash)} {other_slot}."
                ),
            )
        )
        if len(seen) == 3:
            break
    return checks


def check_booking(db: Session, request: BookingCheckRequest) -> BookingCheckResult:
    lab = _get_lab(db, request.lab_id)
    if request.entry_id is not None:
        entry = _get_active_entry(db, request.entry_id)
        dates = entry_dates(entry)
        if request.day_of_week and request.day_of_week != entry.day_of_week:
            dates = _shift_dates(dates, entry.day_of_week, request.day_of_week)
    else:
        assert request.recurrence is not None
        dates = request.recurrence.dates()

    checks = run_checks(
        db,
        lab=lab,
        dates=dates,
        start=request.start_time,
        duration_minutes=request.duration_minutes,
        cohort_size=request.cohort_size,
        subject_codes=request.subject_codes,
        class_type=request.class_type,
        exclude_entry_id=request.entry_id,
    )
    return BookingCheckResult(
        can_save=not any(c.level == "error" for c in checks),
        occurrence_count=len(dates),
        first_date=dates[0] if dates else None,
        last_date=dates[-1] if dates else None,
        checks=checks,
    )


def _raise_if_blocked(checks: list[CheckItem]) -> None:
    errors = [c for c in checks if c.level == "error"]
    if errors:
        raise BookingError(409, " ".join(c.detail for c in errors))


def _write_occurrences(
    db: Session, entry: BaselineScheduleEntry, lab_id: int, dates: list[date]
) -> None:
    entry.occurrences.clear()
    db.flush()
    for occ in expand_occurrences(
        lab_id=lab_id,
        dates=dates,
        start_time=entry.start_time,
        duration_minutes=entry.duration_minutes,
    ):
        entry.occurrences.append(
            ScheduleOccurrence(
                lab_id=occ.lab_id,
                week_number=occ.week_number,
                start_datetime=occ.start_datetime,
                end_datetime=occ.end_datetime,
            )
        )


def create_booking(db: Session, payload: BookingCreate, user: User) -> BaselineScheduleEntry:
    run = active_baseline_run(db)
    if run is None:
        raise BookingError(409, "Upload a timetable baseline before adding bookings.")
    lab = _get_lab(db, payload.lab_id)
    dates = payload.recurrence.dates()
    _raise_if_blocked(
        run_checks(
            db,
            lab=lab,
            dates=dates,
            start=payload.start_time,
            duration_minutes=payload.duration_minutes,
            cohort_size=payload.cohort_size,
            subject_codes=payload.subject_codes,
            class_type=payload.class_type,
            exclude_entry_id=None,
        )
    )

    entry = BaselineScheduleEntry(
        ingestion_run_id=run.id,
        activity_name=payload.activity_name,
        subject_codes=payload.subject_codes,
        class_type=payload.class_type,
        lab_id=lab.id,
        day_of_week=DAY_KEYS[dates[0].weekday()],
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        cohort_size=payload.cohort_size,
        week_pattern_raw=payload.week_pattern_raw,
        teaching_weeks_count=None,
        source="manual",
        status="active",
    )
    db.add(entry)
    db.flush()
    _write_occurrences(db, entry, lab.id, dates)
    db.add(BookingChange(entry_id=entry.id, user_id=user.id, action="create", changes={}))
    db.commit()
    db.refresh(entry)
    return entry


def _lab_code(db: Session, lab_id: int | None) -> str:
    lab = db.get(Lab, lab_id) if lab_id is not None else None
    return lab.code if lab else "—"


def _first_set(*values: object) -> object:
    return next(v for v in values if v is not None)


def update_booking(
    db: Session, entry_id: int, payload: BookingUpdate, user: User
) -> BaselineScheduleEntry:
    entry = _get_active_entry(db, entry_id)
    old_dates = entry_dates(entry)

    new: dict = {
        "activity_name": _first_set(payload.activity_name, entry.activity_name, ""),
        "subject_codes": payload.subject_codes or list(entry.subject_codes),
        "class_type": payload.class_type or entry.class_type,
        "lab_id": _first_set(payload.lab_id, entry.lab_id),
        "day_of_week": payload.day_of_week or entry.day_of_week,
        "start_time": _first_set(payload.start_time, entry.start_time),
        "duration_minutes": payload.duration_minutes or entry.duration_minutes,
        "cohort_size": _first_set(payload.cohort_size, entry.cohort_size),
        "week_pattern_raw": _first_set(payload.week_pattern_raw, entry.week_pattern_raw, ""),
    }
    for nullable in ("activity_name", "week_pattern_raw"):
        new[nullable] = new[nullable] or None
    lab = _get_lab(db, new["lab_id"])

    display = {
        "activity_name": lambda v: v or "—",
        "subject_codes": lambda v: ", ".join(v),
        "class_type": str,
        "lab_id": lambda v: _lab_code(db, v),
        "day_of_week": lambda v: DAY_NAMES[v],
        "start_time": format_time,
        "duration_minutes": lambda v: f"{v // 60}:{v % 60:02d}",
        "cohort_size": str,
        "week_pattern_raw": lambda v: v or "—",
    }
    labels = {"lab_id": "room", "day_of_week": "day", "duration_minutes": "duration"}
    changes: dict[str, list[str]] = {}
    for field, value in new.items():
        old = getattr(entry, field)
        if field == "subject_codes":
            old = list(old)
        if value != old:
            changes[labels.get(field, field)] = [display[field](old), display[field](value)]
    if not changes:
        raise BookingError(400, "Nothing to save — no fields changed.")

    dates = old_dates
    if new["day_of_week"] != entry.day_of_week:
        dates = _shift_dates(old_dates, entry.day_of_week, new["day_of_week"])

    _raise_if_blocked(
        run_checks(
            db,
            lab=lab,
            dates=dates,
            start=new["start_time"],
            duration_minutes=new["duration_minutes"],
            cohort_size=new["cohort_size"],
            subject_codes=new["subject_codes"],
            class_type=new["class_type"],
            exclude_entry_id=entry.id,
        )
    )

    schedule_fields = ("lab_id", "day_of_week", "start_time", "duration_minutes")
    schedule_changed = any(new[f] != getattr(entry, f) for f in schedule_fields)
    for field, value in new.items():
        setattr(entry, field, value)
    if schedule_changed:
        _write_occurrences(db, entry, lab.id, dates)
    db.add(
        BookingChange(
            entry_id=entry.id,
            user_id=user.id,
            action="update",
            changes=changes,
            reason=payload.reason,
        )
    )
    db.commit()
    db.refresh(entry)
    return entry


def cancel_booking(db: Session, entry_id: int, reason: str, user: User) -> BaselineScheduleEntry:
    entry = _get_active_entry(db, entry_id)
    entry.status = "cancelled"
    entry.occurrences.clear()
    db.add(
        BookingChange(
            entry_id=entry.id,
            user_id=user.id,
            action="cancel",
            changes={"status": ["active", "cancelled"]},
            reason=reason,
        )
    )
    db.commit()
    db.refresh(entry)
    return entry


# ---------- reads ----------

_DAY_ORDER = case(
    {key: idx for idx, key in enumerate(DAY_KEYS)}, value=BaselineScheduleEntry.day_of_week
)


def occurrence_stats(db: Session, entry_ids: list[int]) -> dict[int, tuple[int, date, date]]:
    if not entry_ids:
        return {}
    rows = (
        db.query(
            ScheduleOccurrence.baseline_entry_id,
            func.count(ScheduleOccurrence.id),
            func.min(ScheduleOccurrence.start_datetime),
            func.max(ScheduleOccurrence.start_datetime),
        )
        .filter(ScheduleOccurrence.baseline_entry_id.in_(entry_ids))
        .group_by(ScheduleOccurrence.baseline_entry_id)
        .all()
    )
    return {eid: (count, first.date(), last.date()) for eid, count, first, last in rows}


def to_out(
    entry: BaselineScheduleEntry,
    labs: dict[int, Lab],
    occ_stats: dict[int, tuple[int, date, date]],
    clashing: set[int],
) -> dict:
    lab = labs.get(entry.lab_id) if entry.lab_id is not None else None
    count, first, last = occ_stats.get(entry.id, (0, None, None))
    return {
        "id": entry.id,
        "activity_name": entry.activity_name,
        "subject_codes": list(entry.subject_codes),
        "class_type": entry.class_type,
        "lab_id": entry.lab_id,
        "lab_code": lab.code if lab else None,
        "lab_capacity": lab.capacity if lab else None,
        "day_of_week": entry.day_of_week,
        "start_time": entry.start_time,
        "duration_minutes": entry.duration_minutes,
        "cohort_size": entry.cohort_size,
        "week_pattern_raw": entry.week_pattern_raw,
        "source": entry.source,
        "status": entry.status,
        "occurrence_count": count,
        "first_date": first,
        "last_date": last,
        "has_clash": entry.id in clashing,
        "over_capacity": bool(
            lab and lab.capacity is not None and entry.cohort_size > lab.capacity
        ),
    }


def filtered_entries(
    db: Session,
    *,
    q: str | None = None,
    lab_id: int | None = None,
    class_type: str | None = None,
    day: str | None = None,
    flag: str | None = None,
    clashing: set[int] | None = None,
) -> list[BaselineScheduleEntry]:
    query = active_entries(db)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            BaselineScheduleEntry.activity_name.ilike(like)
            | cast(BaselineScheduleEntry.subject_codes, String).ilike(like)
        )
    if lab_id is not None:
        query = query.filter(BaselineScheduleEntry.lab_id == lab_id)
    if class_type:
        query = query.filter(BaselineScheduleEntry.class_type == class_type)
    if day:
        query = query.filter(BaselineScheduleEntry.day_of_week == day)
    if flag == "manual":
        query = query.filter(BaselineScheduleEntry.source == "manual")
    elif flag == "clash":
        query = query.filter(BaselineScheduleEntry.id.in_(clashing or set()))
    elif flag == "over_capacity":
        query = query.join(Lab, BaselineScheduleEntry.lab_id == Lab.id).filter(
            Lab.capacity.is_not(None), BaselineScheduleEntry.cohort_size > Lab.capacity
        )
    return query.order_by(
        _DAY_ORDER, BaselineScheduleEntry.start_time, BaselineScheduleEntry.id
    ).all()


def booking_stats(db: Session, labs: dict[int, Lab], clashing: set[int]) -> dict:
    everything = active_entries(db).all()

    def over(e: BaselineScheduleEntry) -> bool:
        lab = labs.get(e.lab_id) if e.lab_id is not None else None
        return bool(lab and lab.capacity is not None and e.cohort_size > lab.capacity)

    return {
        "total": len(everything),
        "manual": sum(1 for e in everything if e.source == "manual"),
        "clashes": len(clashing),
        "over_capacity": sum(1 for e in everything if over(e)),
    }


def list_bookings(
    db: Session,
    *,
    q: str | None,
    lab_id: int | None,
    class_type: str | None,
    day: str | None,
    flag: str | None,
    page: int,
    page_size: int,
) -> dict:
    labs = {lab.id: lab for lab in db.query(Lab).all()}
    clashing = all_clashing_entry_ids(db)
    entries = filtered_entries(
        db, q=q, lab_id=lab_id, class_type=class_type, day=day, flag=flag, clashing=clashing
    )
    page_entries = entries[(page - 1) * page_size : page * page_size]
    occ_stats = occurrence_stats(db, [e.id for e in page_entries])
    return {
        "items": [to_out(e, labs, occ_stats, clashing) for e in page_entries],
        "total": len(entries),
        "page": page,
        "page_size": page_size,
        "stats": booking_stats(db, labs, clashing),
    }


def booking_detail(db: Session, entry_id: int) -> dict:
    entry = db.get(BaselineScheduleEntry, entry_id)
    if entry is None:
        raise BookingError(404, "Booking not found.")
    labs = {lab.id: lab for lab in db.query(Lab).all()}
    clashing = all_clashing_entry_ids(db) if entry.status == "active" else set()
    out = to_out(entry, labs, occurrence_stats(db, [entry.id]), clashing)
    history = (
        db.query(BookingChange, User.full_name)
        .outerjoin(User, BookingChange.user_id == User.id)
        .filter(BookingChange.entry_id == entry.id)
        .order_by(BookingChange.created_at.desc(), BookingChange.id.desc())
        .all()
    )
    out["dates"] = entry_dates(entry)
    out["history"] = [
        {
            "id": change.id,
            "action": change.action,
            "changes": change.changes,
            "reason": change.reason,
            "user_name": name,
            "created_at": change.created_at,
        }
        for change, name in history
    ]
    return out
