from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    building: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer)
    room_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    weekly_available_hours: Mapped[float] = mapped_column(Numeric(6, 2), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
