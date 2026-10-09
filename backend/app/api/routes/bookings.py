import io
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.bookings import service
from app.bookings.clashes import active_entries, all_clashing_entry_ids
from app.db.models.baseline import BaselineScheduleEntry
from app.db.models.lab import Lab
from app.db.models.user import ROLE_ADMIN, ROLE_STAFF, User
from app.db.session import get_db
from app.schemas.booking import (
    BookingCancel,
    BookingCheckRequest,
    BookingCheckResult,
    BookingCreate,
    BookingDetail,
    BookingList,
    BookingUpdate,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])

staff_or_admin = require_roles(ROLE_ADMIN, ROLE_STAFF)
admin_only = require_roles(ROLE_ADMIN)

DayParam = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
FlagParam = Literal["manual", "clash", "over_capacity"]


def _http(exc: service.BookingError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("", response_model=BookingList)
def list_bookings(
    q: str | None = None,
    lab_id: int | None = None,
    class_type: str | None = None,
    day: DayParam | None = None,
    flag: FlagParam | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(staff_or_admin),
) -> dict:
    return service.list_bookings(
        db,
        q=q,
        lab_id=lab_id,
        class_type=class_type,
        day=day,
        flag=flag,
        page=page,
        page_size=page_size,
    )


@router.get("/class-types", response_model=list[str])
def class_types(db: Session = Depends(get_db), _: User = Depends(staff_or_admin)) -> list[str]:
    rows = active_entries(db).with_entities(BaselineScheduleEntry.class_type).distinct().all()
    return sorted({row[0] for row in rows})


@router.get("/export.xlsx")
def export_bookings(
    q: str | None = None,
    lab_id: int | None = None,
    class_type: str | None = None,
    day: DayParam | None = None,
    flag: FlagParam | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(staff_or_admin),
) -> StreamingResponse:
    labs = {lab.id: lab for lab in db.query(Lab).all()}
    clashing = all_clashing_entry_ids(db)
    entries = service.filtered_entries(
        db, q=q, lab_id=lab_id, class_type=class_type, day=day, flag=flag, clashing=clashing
    )
    occ_stats = service.occurrence_stats(db, [e.id for e in entries])
    rows = []
    for entry in entries:
        out = service.to_out(entry, labs, occ_stats, clashing)
        rows.append(
            {
                "Activity Type": out["class_type"],
                "Subject(s)": ", ".join(out["subject_codes"]),
                "Class": out["activity_name"],
                "Room": out["lab_code"],
                "Day": service.DAY_NAMES[out["day_of_week"]],
                "Time": service.slot_label(
                    out["day_of_week"], out["start_time"], out["duration_minutes"]
                ).split(" ", 1)[1],
                "Duration (min)": out["duration_minutes"],
                "Cohort size": out["cohort_size"],
                "Room capacity": out["lab_capacity"],
                "Occurrences": out["occurrence_count"],
                "First date": out["first_date"],
                "Last date": out["last_date"],
                "Teaching week pattern": out["week_pattern_raw"],
                "Source": out["source"],
                "Room clash": "Yes" if out["has_clash"] else "",
                "Over capacity": "Yes" if out["over_capacity"] else "",
            }
        )
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False, sheet_name="Bookings")
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="scit-bookings.xlsx"'},
    )


@router.post("/check", response_model=BookingCheckResult)
def check_booking(
    payload: BookingCheckRequest,
    db: Session = Depends(get_db),
    _: User = Depends(staff_or_admin),
) -> BookingCheckResult:
    try:
        return service.check_booking(db, payload)
    except service.BookingError as exc:
        raise _http(exc) from exc


@router.get("/{entry_id}", response_model=BookingDetail)
def get_booking(
    entry_id: int, db: Session = Depends(get_db), _: User = Depends(staff_or_admin)
) -> dict:
    try:
        return service.booking_detail(db, entry_id)
    except service.BookingError as exc:
        raise _http(exc) from exc


@router.post("", response_model=BookingDetail, status_code=201)
def create_booking(
    payload: BookingCreate, db: Session = Depends(get_db), user: User = Depends(admin_only)
) -> dict:
    try:
        entry = service.create_booking(db, payload, user)
    except service.BookingError as exc:
        raise _http(exc) from exc
    return service.booking_detail(db, entry.id)


@router.patch("/{entry_id}", response_model=BookingDetail)
def update_booking(
    entry_id: int,
    payload: BookingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
) -> dict:
    try:
        service.update_booking(db, entry_id, payload, user)
    except service.BookingError as exc:
        raise _http(exc) from exc
    return service.booking_detail(db, entry_id)


@router.post("/{entry_id}/cancel", response_model=BookingDetail)
def cancel_booking(
    entry_id: int,
    payload: BookingCancel,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
) -> dict:
    try:
        service.cancel_booking(db, entry_id, payload.reason, user)
    except service.BookingError as exc:
        raise _http(exc) from exc
    return service.booking_detail(db, entry_id)
