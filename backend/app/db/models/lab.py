from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Lab(Base):
    """A physical room. `capacity` is populated from the export's "Capicity"
    column during ingestion (app/ingestion/service.py); it stays null for a
    freshly-seeded room that hasn't been through an ingestion run yet.
    `weekly_available_hours` has no equivalent column in the export, so it
    stays null (unknown) until confirmed with the client. Both are nullable,
    not defaulted to 0, since 0 would falsely read as "no capacity" rather
    than "unknown".
    """

    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    building: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    weekly_available_hours: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
