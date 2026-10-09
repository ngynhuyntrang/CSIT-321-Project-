from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.db.models.user import STATUS_ACTIVE, AuthSession, User
from app.db.session import get_db


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_current_session(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> AuthSession:
    token = _bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    session = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).first()
    # SQLite returns naive datetimes; sessions are always written in UTC.
    now = datetime.now(UTC).replace(tzinfo=None)
    if session is None or session.expires_at.replace(tzinfo=None) <= now:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    if session.user.status != STATUS_ACTIVE:
        raise HTTPException(status_code=403, detail="Account is not active.")
    return session


def get_current_user(session: AuthSession = Depends(get_current_session)) -> User:
    return session.user


def require_roles(*roles: str) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You don't have access to this.")
        return user

    return dependency
