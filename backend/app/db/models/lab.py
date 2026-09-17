from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Lab(Base):
    """A physical room. `capacity` and `weekly_available_hours` are nullable,
    not defaulted to 0 -- the Enterprise export carries no room-capacity or
    operating-hours data, and 0 would falsely read as "no capacity" rather
    than "unknown". Leave them null until confirmed with the client.
    """

    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    building: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    weekly_available_hours: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
