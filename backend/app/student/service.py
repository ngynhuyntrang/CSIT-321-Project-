"""Student-facing views over the active baseline (prototype screens 10-12).

Teaching periods are derived from the export's own dates: bookings whose
first-to-last date ranges overlap belong to the same period (e.g. the real
export holds an Autumn and a Spring session). Nothing is inferred from class
names or week numbers.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.bookings.clashes import Interval, active_entries, overlaps
from app.bookings.service import DAY_KEYS, occurrence_stats
from app.core.config import get_settings
from app.db.models.baseline import BaselineScheduleEntry, ScheduleOccurrence
from app.db.models.lab import Lab
from app.db.models.student import ClassSelection, StudentSubject
from app.db.models.user import User


class StudentError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class Period:
    start: date
    end: date

    @property
    def id(self) -> str:
        return self.start.isoformat()

    def contains(self, first: date, last: date) -> bool:
        return self.start <= first and last <= self.end

    def to_dict(self) -> dict:
        return {"id": self.id, "start": self.start, "end": self.end}


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def teaching_periods(db: Session) -> list[Period]:
    ids = [eid for (eid,) in active_entries(db).with_entities(BaselineScheduleEntry.id).all()]
    ranges = sorted((first, last) for _, first, last in occurrence_stats(db, ids).values())
    periods: list[Period] = []
    for first, last in ranges:
        if periods and first <= periods[-1].end:
            periods[-1].end = max(periods[-1].end, last)
        else:
            periods.append(Period(first, last))
    return periods


def resolve_period(db: Session, period_id: str | None, today: date) -> Period | None:
    periods = teaching_periods(db)
    if not periods:
        return None
    if period_id:
        for period in periods:
            if period.id == period_id:
                return period
        raise StudentError(404, "Unknown teaching period.")
    for period in periods:
        if period.start <= today <= period.end:
            return period
    upcoming = [p for p in periods if p.start > today]
    return upcoming[0] if upcoming else periods[-1]


def _entry_intervals(db: Session, entry_ids: list[int]) -> dict[int, list[Interval]]:
    result: dict[int, list[Interval]] = defaultdict(list)
    if not entry_ids:
        return result
    rows = (
        db.query(
            ScheduleOccurrence.baseline_entry_id,
            ScheduleOccurrence.start_datetime,
            ScheduleOccurrence.end_datetime,
        )
        .filter(ScheduleOccurrence.baseline_entry_id.in_(entry_ids))
        .all()
    )
    for entry_id, start, end in rows:
        result[entry_id].append((start, end))
    return result


def _intervals_clash(a: list[Interval], b: list[Interval]) -> bool:
    return any(overlaps(x, y) for x in a for y in b)


def _pick_counts(db: Session, entry_ids: list[int]) -> dict[int, int]:
    if not entry_ids:
        return {}
    rows = (
        db.query(ClassSelection.entry_id, func.count(ClassSelection.id))
        .filter(ClassSelection.entry_id.in_(entry_ids))
        .group_by(ClassSelection.entry_id)
        .all()
    )
    return dict(rows)


def seats_left(capacity: int | None, cohort_size: int, picks: int) -> int | None:
    """Room capacity - export cohort size - students who picked it here.
    None means the room's capacity is unknown."""
    if capacity is None:
        return None
    return max(0, capacity - cohort_size - picks)


def _subject_codes(db: Session, user: User) -> list[str]:
    rows = db.query(StudentSubject.subject_code).filter(StudentSubject.user_id == user.id).all()
    return sorted(code for (code,) in rows)


def _selected_entries(db: Session, user: User) -> list[BaselineScheduleEntry]:
    selected_ids = (
        db.query(ClassSelection.entry_id).filter(ClassSelection.user_id == user.id).scalar_subquery()
    )
    return active_entries(db).filter(BaselineScheduleEntry.id.in_(selected_ids)).all()


def _shares_subject(entry: BaselineScheduleEntry, codes: set[str]) -> bool:
    return bool(codes & set(entry.subject_codes))


def _same_slot(a: BaselineScheduleEntry, b: BaselineScheduleEntry) -> bool:
    """Two bookings fill the same slot in a timetable: same subject and type."""
    return a.class_type == b.class_type and bool(set(a.subject_codes) & set(b.subject_codes))


def available_subjects(db: Session, period: Period | None) -> list[str]:
    entries = active_entries(db).all()
    stats = occurrence_stats(db, [e.id for e in entries])
    codes: set[str] = set()
    for entry in entries:
        if entry.id not in stats:
            continue
        _, first, last = stats[entry.id]
        if period is None or period.contains(first, last):
            codes.update(entry.subject_codes)
    return sorted(codes)


def class_options(db: Session, user: User, period_id: str | None, today: date) -> dict:
    period = resolve_period(db, period_id, today)
    subjects = _subject_codes(db, user)
    labs = {lab.id: lab for lab in db.query(Lab).all()}
    if period is None:
        return {"period": None, "periods": [], "subjects": [], "on_campus_days": []}

    entries = active_entries(db).all()
    stats = occurrence_stats(db, [e.id for e in entries])
    in_period = [
        e for e in entries if e.id in stats and period.contains(stats[e.id][1], stats[e.id][2])
    ]
    selected = [e for e in _selected_entries(db, user) if e in in_period]
    selected_ids = {e.id for e in selected}
    relevant = [e for e in in_period if _shares_subject(e, set(subjects))]
    intervals = _entry_intervals(db, [e.id for e in relevant] + list(selected_ids))
    picks = _pick_counts(db, [e.id for e in relevant])

    current_days = {e.day_of_week for e in selected}
    subject_out = []
    for code in subjects:
        groups: dict[str, list[dict]] = defaultdict(list)
        for entry in sorted(
            (e for e in relevant if code in e.subject_codes),
            key=lambda e: (DAY_KEYS.index(e.day_of_week), e.start_time, e.id),
        ):
            others = [s for s in selected if not _same_slot(s, entry)]
            lab = labs.get(entry.lab_id) if entry.lab_id is not None else None
            left = seats_left(lab.capacity if lab else None, entry.cohort_size, picks.get(entry.id, 0))
            is_selected = entry.id in selected_ids
            # Choosing this replaces any pick in the same slot, so compare the
            # resulting set of days with today's, not just "is the day new".
            days_after = {s.day_of_week for s in others} | {entry.day_of_week}
            groups[entry.class_type].append(
                {
                    "entry_id": entry.id,
                    "activity_name": entry.activity_name,
                    "class_type": entry.class_type,
                    "day_of_week": entry.day_of_week,
                    "start_time": entry.start_time,
                    "duration_minutes": entry.duration_minutes,
                    "lab_code": lab.code if lab else None,
                    "capacity": lab.capacity if lab else None,
                    "cohort_size": entry.cohort_size,
                    "picks": picks.get(entry.id, 0),
                    "seats_left": left,
                    "full": left == 0 and not is_selected,
                    "selected": is_selected,
                    "clashes_with": sorted(
                        {
                            s.activity_name or "/".join(s.subject_codes)
                            for s in others
                            if _intervals_clash(intervals[s.id], intervals[entry.id])
                        }
                    ),
                    "adds_day": len(days_after) > len(current_days),
                    "days_after": len(days_after),
                    "first_date": stats[entry.id][1],
                    "last_date": stats[entry.id][2],
                    "occurrence_count": stats[entry.id][0],
                }
            )
        subject_out.append(
            {
                "subject_code": code,
                "groups": [{"class_type": t, "options": opts} for t, opts in sorted(groups.items())],
            }
        )

    return {
        "period": period.to_dict(),
        "periods": [p.to_dict() for p in teaching_periods(db)],
        "subjects": subject_out,
        "on_campus_days": sorted(
            {e.day_of_week for e in selected}, key=DAY_KEYS.index
        ),
    }


def _period_of(db: Session, entry: BaselineScheduleEntry) -> Period | None:
    stats = occurrence_stats(db, [entry.id]).get(entry.id)
    if stats is None:
        return None
    _, first, last = stats
    return next((p for p in teaching_periods(db) if p.contains(first, last)), None)


def select_class(db: Session, user: User, entry_id: int) -> None:
    entry = active_entries(db).filter(BaselineScheduleEntry.id == entry_id).first()
    if entry is None:
        raise StudentError(404, "That class is no longer in the timetable.")
    subjects = set(_subject_codes(db, user))
    if not _shares_subject(entry, subjects):
        raise StudentError(400, "Add the subject to your list before choosing its classes.")
    period = _period_of(db, entry)

    current = [e for e in _selected_entries(db, user) if _period_of(db, e) == period]
    if any(e.id == entry.id for e in current):
        return
    replaced = [e for e in current if _same_slot(e, entry)]
    others = [e for e in current if not _same_slot(e, entry)]

    lab = db.get(Lab, entry.lab_id) if entry.lab_id is not None else None
    picks = _pick_counts(db, [entry.id]).get(entry.id, 0)
    if seats_left(lab.capacity if lab else None, entry.cohort_size, picks) == 0:
        raise StudentError(409, f"{entry.activity_name or 'This class'} is full.")

    intervals = _entry_intervals(db, [entry.id] + [e.id for e in others])
    clashing = [e for e in others if _intervals_clash(intervals[e.id], intervals[entry.id])]
    if clashing:
        names = ", ".join(e.activity_name or "/".join(e.subject_codes) for e in clashing)
        raise StudentError(409, f"Clashes with your {names}.")

    for old in replaced:
        db.query(ClassSelection).filter(
            ClassSelection.user_id == user.id, ClassSelection.entry_id == old.id
        ).delete()
    db.add(ClassSelection(user_id=user.id, entry_id=entry.id))
    db.commit()


def unselect_class(db: Session, user: User, entry_id: int) -> None:
    db.query(ClassSelection).filter(
        ClassSelection.user_id == user.id, ClassSelection.entry_id == entry_id
    ).delete()
    db.commit()


def add_subject(db: Session, user: User, code: str, period_id: str | None, today: date) -> None:
    code = code.strip().upper()
    period = resolve_period(db, period_id, today)
    if code not in available_subjects(db, period):
        raise StudentError(404, f"No {code} classes in this teaching period's timetable.")
    exists = (
        db.query(StudentSubject)
        .filter(StudentSubject.user_id == user.id, StudentSubject.subject_code == code)
        .first()
    )
    if exists is None:
        db.add(StudentSubject(user_id=user.id, subject_code=code))
        db.commit()

    # Auto-pick any class type that has exactly one class in this period
    # (e.g. a single lecture), if it has room and doesn't clash.
    options = class_options(db, user, period.id if period else None, today)
    for subject in options["subjects"]:
        if subject["subject_code"] != code:
            continue
        for group in subject["groups"]:
            opts = group["options"]
            if len(opts) == 1 and not opts[0]["selected"]:
                try:
                    select_class(db, user, opts[0]["entry_id"])
                except StudentError:
                    pass


def remove_subject(db: Session, user: User, code: str) -> None:
    code = code.strip().upper()
    for entry in _selected_entries(db, user):
        if code in entry.subject_codes:
            unselect_class(db, user, entry.id)
    db.query(StudentSubject).filter(
        StudentSubject.user_id == user.id, StudentSubject.subject_code == code
    ).delete()
    db.commit()


def timetable(db: Session, user: User, week_start: date | None, now: datetime) -> dict:
    labs = {lab.id: lab for lab in db.query(Lab).all()}
    selected = {e.id: e for e in _selected_entries(db, user)}
    occurrences = (
        db.query(ScheduleOccurrence)
        .filter(ScheduleOccurrence.baseline_entry_id.in_(list(selected)))
        .order_by(ScheduleOccurrence.start_datetime)
        .all()
        if selected
        else []
    )
    weeks = sorted({monday_of(o.start_datetime.date()) for o in occurrences})
    if week_start is None:
        this_week = monday_of(now.date())
        upcoming = [w for w in weeks if w >= this_week]
        week_start = this_week if this_week in weeks or not weeks else (upcoming or weeks)[0]
    week_start = monday_of(week_start)
    week_end = week_start + timedelta(days=7)

    def event(o: ScheduleOccurrence) -> dict:
        entry = selected[o.baseline_entry_id]
        lab = labs.get(o.lab_id)
        return {
            "entry_id": entry.id,
            "subject_codes": list(entry.subject_codes),
            "activity_name": entry.activity_name,
            "class_type": entry.class_type,
            "lab_code": lab.code if lab else None,
            "start": o.start_datetime,
            "end": o.end_datetime,
            "day_of_week": DAY_KEYS[o.start_datetime.weekday()],
        }

    events = [event(o) for o in occurrences if week_start <= o.start_datetime.date() < week_end]
    next_class = next((event(o) for o in occurrences if o.end_datetime > now), None)
    return {
        "week_start": week_start,
        "weeks": weeks,
        "events": events,
        "on_campus_days": sorted({e["day_of_week"] for e in events}, key=DAY_KEYS.index),
        "next_class": next_class,
        "selected_count": len(selected),
    }


def _parse_hhmm(value: str) -> time:
    hours, minutes = value.split(":")
    return time(int(hours), int(minutes))


def _merge(intervals: list[Interval]) -> list[Interval]:
    merged: list[Interval] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def availability(db: Session, week_start: date | None, now: datetime) -> dict:
    settings = get_settings()
    day_start, day_end = _parse_hhmm(settings.student_day_start), _parse_hhmm(settings.student_day_end)
    week_start = monday_of(week_start or now.date())
    days = [week_start + timedelta(days=i) for i in range(5)]
    labs = db.query(Lab).filter(Lab.active.is_(True)).order_by(Lab.code).all()

    active_ids = active_entries(db).with_entities(BaselineScheduleEntry.id).scalar_subquery()
    rows = (
        db.query(ScheduleOccurrence.lab_id, ScheduleOccurrence.start_datetime, ScheduleOccurrence.end_datetime)
        .filter(ScheduleOccurrence.baseline_entry_id.in_(active_ids))
        .filter(ScheduleOccurrence.start_datetime < datetime.combine(days[-1], day_end))
        .filter(ScheduleOccurrence.end_datetime > datetime.combine(days[0], day_start))
        .all()
    )
    busy: dict[tuple[int, date], list[Interval]] = defaultdict(list)
    for lab_id, start, end in rows:
        busy[(lab_id, start.date())].append((start, end))

    window_minutes = (
        datetime.combine(date.min, day_end) - datetime.combine(date.min, day_start)
    ).total_seconds() / 60
    rooms = []
    for lab in labs:
        free_by_day = {}
        for day in days:
            window = (datetime.combine(day, day_start), datetime.combine(day, day_end))
            blocks = [
                (max(s, window[0]), min(e, window[1]))
                for s, e in _merge(busy[(lab.id, day)])
                if overlaps((s, e), window)
            ]
            used = sum((e - s).total_seconds() / 60 for s, e in blocks)
            free_by_day[DAY_KEYS[day.weekday()]] = round(window_minutes - used)
        rooms.append({"lab_id": lab.id, "lab_code": lab.code, "capacity": lab.capacity, "free_minutes": free_by_day})

    free_now = None
    today_window = (datetime.combine(now.date(), day_start), datetime.combine(now.date(), day_end))
    if now.weekday() < 5 and today_window[0] <= now < today_window[1]:
        free_now = []
        for lab in labs:
            today_busy = _merge(_busy_on(db, lab.id, now.date(), active_ids))
            current = next((b for b in today_busy if b[0] <= now < b[1]), None)
            if current:
                free_now.append(
                    {"lab_code": lab.code, "capacity": lab.capacity, "free": False, "until": current[1]}
                )
                continue
            next_start = next((b[0] for b in today_busy if b[0] > now), today_window[1])
            free_now.append(
                {
                    "lab_code": lab.code,
                    "capacity": lab.capacity,
                    "free": True,
                    "until": min(next_start, today_window[1]),
                }
            )
        free_now.sort(key=lambda r: (not r["free"], r["lab_code"]))

    return {
        "week_start": week_start,
        "day_start": settings.student_day_start,
        "day_end": settings.student_day_end,
        "has_bookings": bool(rows),
        "rooms": rooms,
        "now": now,
        "free_now": free_now,
    }


def _busy_on(db: Session, lab_id: int, day: date, active_ids: object) -> list[Interval]:
    """A room's bookings on one day (today may be outside the requested week)."""
    rows = (
        db.query(ScheduleOccurrence.start_datetime, ScheduleOccurrence.end_datetime)
        .filter(ScheduleOccurrence.baseline_entry_id.in_(active_ids))
        .filter(ScheduleOccurrence.lab_id == lab_id)
        .filter(ScheduleOccurrence.start_datetime >= datetime.combine(day, time.min))
        .filter(ScheduleOccurrence.start_datetime < datetime.combine(day + timedelta(days=1), time.min))
        .all()
    )
    return [(s, e) for s, e in rows]
