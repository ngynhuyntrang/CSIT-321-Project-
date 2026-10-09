from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models.user import ROLE_ADMIN, User
from app.db.session import get_db
from app.schemas.auth import UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

admin_only = require_roles(ROLE_ADMIN)


@router.get("", response_model=list[UserOut])
def list_users(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> list[User]:
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    return query.order_by(User.created_at.desc()).all()


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == admin.id and (payload.role or payload.status):
        raise HTTPException(status_code=400, detail="You can't change your own role or status.")
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        user.status = payload.status
        if payload.status != "active":
            user.sessions.clear()
    db.commit()
    db.refresh(user)
    return user
