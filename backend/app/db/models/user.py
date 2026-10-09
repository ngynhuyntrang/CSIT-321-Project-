from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

ROLE_STUDENT = "student"
ROLE_STAFF = "staff"
ROLE_ADMIN = "admin"
ROLES = (ROLE_STUDENT, ROLE_STAFF, ROLE_ADMIN)

STATUS_ACTIVE = "active"
STATUS_PENDING = "pending"
STATUS_DISABLED = "disabled"
STATUSES = (STATUS_ACTIVE, STATUS_PENDING, STATUS_DISABLED)


class User(Base):
    """An account. `role="staff"` sign-ups start `pending` until an admin
    approves them, since staff can see internal timetabling data (A2 RBAC);
    students are `active` immediately.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    student_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(10), default=ROLE_STUDENT)
    status: Mapped[str] = mapped_column(String(10), default=STATUS_ACTIVE)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthSession(Base):
    """A signed-in session. Only the sha256 of the bearer token is stored, so
    a leaked database row can't be replayed as a login."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    user: Mapped["User"] = relationship(back_populates="sessions")
