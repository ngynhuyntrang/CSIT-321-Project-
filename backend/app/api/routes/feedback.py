from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models.baseline import BaselineScheduleEntry
from app.db.models.lab import Lab
from app.db.models.student import Feedback
from app.db.models.user import ROLE_ADMIN, ROLE_STAFF, ROLE_STUDENT, User
from app.db.session import get_db
from app.schemas.student import FeedbackCreate, FeedbackOut, FeedbackUpdate

router = APIRouter(prefix="/feedback", tags=["feedback"])

student_only = require_roles(ROLE_STUDENT)
staff_or_admin = require_roles(ROLE_ADMIN, ROLE_STAFF)


def _out(db: Session, fb: Feedback, *, reveal_author: bool) -> dict:
    entry = db.get(BaselineScheduleEntry, fb.entry_id) if fb.entry_id else None
    lab_id = fb.lab_id or (entry.lab_id if entry else None)
    lab = db.get(Lab, lab_id) if lab_id else None
    author = None
    if reveal_author and not fb.anonymous:
        user = db.get(User, fb.user_id)
        author = user.full_name if user else None
    return {
        "id": fb.id,
        "entry_id": fb.entry_id,
        "class_label": (
            f"{'/'.join(entry.subject_codes)} · {entry.class_type}"
            + (f" ({entry.activity_name})" if entry.activity_name else "")
            if entry
            else None
        ),
        "lab_code": lab.code if lab else None,
        "category": fb.category,
        "rating": fb.rating,
        "comment": fb.comment,
        "anonymous": fb.anonymous,
        "status": fb.status,
        "author": author,
        "created_at": fb.created_at,
    }


@router.post("", response_model=FeedbackOut, status_code=201)
def create_feedback(
    payload: FeedbackCreate, db: Session = Depends(get_db), user: User = Depends(student_only)
) -> dict:
    if payload.entry_id is not None and db.get(BaselineScheduleEntry, payload.entry_id) is None:
        raise HTTPException(status_code=404, detail="Class not found.")
    if payload.lab_id is not None and db.get(Lab, payload.lab_id) is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    fb = Feedback(user_id=user.id, **payload.model_dump())
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return _out(db, fb, reveal_author=False)


@router.get("/mine", response_model=list[FeedbackOut])
def my_feedback(db: Session = Depends(get_db), user: User = Depends(student_only)) -> list[dict]:
    rows = (
        db.query(Feedback)
        .filter(Feedback.user_id == user.id)
        .order_by(Feedback.created_at.desc())
        .all()
    )
    return [_out(db, fb, reveal_author=False) for fb in rows]


@router.get("", response_model=list[FeedbackOut])
def list_feedback(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(staff_or_admin),
) -> list[dict]:
    query = db.query(Feedback)
    if status:
        query = query.filter(Feedback.status == status)
    return [_out(db, fb, reveal_author=True) for fb in query.order_by(Feedback.created_at.desc())]


@router.patch("/{feedback_id}", response_model=FeedbackOut)
def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
) -> dict:
    fb = db.get(Feedback, feedback_id)
    if fb is None:
        raise HTTPException(status_code=404, detail="Feedback not found.")
    fb.status = payload.status
    db.commit()
    db.refresh(fb)
    return _out(db, fb, reveal_author=True)
