from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import get_settings
from app.db.models.user import ROLE_STUDENT, User
from app.db.session import get_db
from app.schemas.student import (
    AddSubject,
    AvailabilityOut,
    ClassOptionsOut,
    PeriodOut,
    SelectClass,
    TimetableOut,
)
from app.student import service

router = APIRouter(tags=["student"])

student_only = require_roles(ROLE_STUDENT)


def _now() -> datetime:
    # Occurrence times are stored as naive campus wall-clock time.
    return datetime.now(ZoneInfo(get_settings().campus_timezone)).replace(tzinfo=None)


def _http(exc: service.StudentError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/periods", response_model=list[PeriodOut])
def periods(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[dict]:
    return [p.to_dict() for p in service.teaching_periods(db)]


@router.get("/subjects", response_model=list[str])
def subjects(
    period_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[str]:
    try:
        period = service.resolve_period(db, period_id, _now().date())
    except service.StudentError as exc:
        raise _http(exc) from exc
    return service.available_subjects(db, period)


@router.get("/student/classes", response_model=ClassOptionsOut)
def class_options(
    period_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
) -> dict:
    try:
        return service.class_options(db, user, period_id, _now().date())
    except service.StudentError as exc:
        raise _http(exc) from exc


@router.post("/student/subjects", status_code=204)
def add_subject(
    payload: AddSubject, db: Session = Depends(get_db), user: User = Depends(student_only)
) -> None:
    try:
        service.add_subject(db, user, payload.subject_code, payload.period_id, _now().date())
    except service.StudentError as exc:
        raise _http(exc) from exc


@router.delete("/student/subjects/{code}", status_code=204)
def remove_subject(
    code: str, db: Session = Depends(get_db), user: User = Depends(student_only)
) -> None:
    service.remove_subject(db, user, code)


@router.put("/student/selections", status_code=204)
def select_class(
    payload: SelectClass, db: Session = Depends(get_db), user: User = Depends(student_only)
) -> None:
    try:
        service.select_class(db, user, payload.entry_id)
    except service.StudentError as exc:
        raise _http(exc) from exc


@router.delete("/student/selections/{entry_id}", status_code=204)
def unselect_class(
    entry_id: int, db: Session = Depends(get_db), user: User = Depends(student_only)
) -> None:
    service.unselect_class(db, user, entry_id)


@router.get("/student/timetable", response_model=TimetableOut)
def timetable(
    week_start: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(student_only),
) -> dict:
    return service.timetable(db, user, week_start, _now())


@router.get("/rooms/availability", response_model=AvailabilityOut)
def availability(
    week_start: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    return service.availability(db, week_start, _now())
