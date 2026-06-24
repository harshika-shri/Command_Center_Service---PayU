from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from pydantic import BaseModel, Field


class ReportDateFilterParams(BaseModel):
    start_date: date | None = None
    end_date: date | None = None


class ReportSummaryResponse(BaseModel):
    total_invoices: int
    under_review: int
    ready_to_pay: int
    rejected: int
    escalated: int


class ReportPerformanceResponse(BaseModel):
    avg_approval_time_hours: float = Field(
        default=0.0,
    )
    avg_rejection_time_hours: float = Field(
        default=0.0,
    )


class VendorSummaryItem(BaseModel):
    vendor_name: str
    invoice_count: int


class AssociateWorkloadItem(BaseModel):
    associate_name: str
    under_review: int
    approved: int
    rejected: int
    escalated: int


class ManagerWorkloadItem(BaseModel):
    manager_name: str
    escalated: int
    claimed_unresolved: int
    approved: int
    rejected: int


def to_utc_start(
    value: date,
) -> datetime:
    return datetime.combine(
        value,
        time.min,
        tzinfo=UTC,
    )


def to_utc_end_exclusive(
    value: date,
) -> datetime:
    return datetime.combine(
        value + timedelta(
            days=1,
        ),
        time.min,
        tzinfo=UTC,
    )
