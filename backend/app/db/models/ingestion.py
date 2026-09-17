from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    status: Mapped[str] = mapped_column(String(20), default="processing")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    is_active_baseline: Mapped[bool] = mapped_column(default=False)

    errors: Mapped[list["IngestionError"]] = relationship(
        back_populates="ingestion_run", cascade="all, delete-orphan"
    )


class IngestionError(Base):
    __tablename__ = "ingestion_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingestion_run_id: Mapped[int] = mapped_column(ForeignKey("ingestion_runs.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    field: Mapped[str] = mapped_column(String(100))
    error_type: Mapped[str] = mapped_column(String(50))
    raw_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(String(500))

    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="errors")
