from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_current_user
from app.core.security import hash_password, hash_token, new_session_token, verify_password
from app.db.models.user import (
    ROLE_STAFF,
    STATUS_ACTIVE,
    STATUS_PENDING,
    AuthSession,
    User,
)
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, SignupRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_TTL = timedelta(hours=12)
REMEMBER_ME_TTL = timedelta(days=30)


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        student_number=payload.student_number or None,
        role=payload.role,
        status=STATUS_PENDING if payload.role == ROLE_STAFF else STATUS_ACTIVE,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if user.status == STATUS_PENDING:
        raise HTTPException(
            status_code=403, detail="Your staff account is awaiting approval by SCIT Operations."
        )
    if user.status != STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="This account has been disabled.")

    token = new_session_token()
    now = datetime.now(UTC).replace(tzinfo=None)
    expires_at = now + (REMEMBER_ME_TTL if payload.remember_me else SESSION_TTL)
    # Housekeeping: drop this user's expired sessions so the table doesn't grow forever.
    db.query(AuthSession).filter(
        AuthSession.user_id == user.id, AuthSession.expires_at <= now
    ).delete()
    db.add(AuthSession(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at))
    db.commit()
    return {"token": token, "expires_at": expires_at, "user": user}


@router.post("/logout", status_code=204)
def logout(
    session: AuthSession = Depends(get_current_session), db: Session = Depends(get_db)
) -> None:
    db.delete(session)
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
