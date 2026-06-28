from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.postgres.base import Base


class SystemJob(Base):
    __tablename__ = "system_jobs"

    job_name: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    last_run_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
