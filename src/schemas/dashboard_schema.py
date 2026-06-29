from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    ready_for_approval: int
    needs_review: int
    escalated: int
    ready_to_pay: int
    rejected: int
    overdue: int
    total: int


class DashboardInvoiceListItem(BaseModel):
    invoice_id: UUID
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None = None
    vendor_name: str | None
    total_amount: float | None
    validation_outcome: str | None
    invoice_status: str | None
    rejection_reason: str | None = None
    escalated_to: UUID | None = None
    assigned_manager_id: UUID | None = None
    created_at: datetime


class DashboardInvoiceListResponse(BaseModel):
    items: list[DashboardInvoiceListItem]
    page: int
    page_size: int
    total_records: int


class DashboardPaginationParams(BaseModel):
    page: int = Field(
        default=1,
        ge=1,
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
