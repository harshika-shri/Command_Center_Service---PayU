from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.query.search_filter_builder import (
    InvoiceListFilters,
    ReportFilters,
)


class InvoiceListQueryParams(BaseModel):
    search: str | None = None
    invoice_status: str | None = None
    validation_outcome: str | None = None
    vendor_id: UUID | None = None
    associate_id: UUID | None = None
    manager_id: UUID | None = None
    from_date: date | None = None
    to_date: date | None = None
    page: int = Field(
        default=1,
        ge=1,
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )
    sort_by: str = Field(
        default="created_at",
    )
    sort_order: str = Field(
        default="desc",
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def to_filters(self) -> InvoiceListFilters:
        return InvoiceListFilters(
            search=self.search,
            invoice_status=self.invoice_status,
            validation_outcome=self.validation_outcome,
            vendor_id=self.vendor_id,
            associate_id=self.associate_id,
            manager_id=self.manager_id,
            from_date=self.from_date,
            to_date=self.to_date,
        )


class ReportFilterParams(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    invoice_status: str | None = None
    validation_outcome: str | None = None
    vendor_id: UUID | None = None
    associate_id: UUID | None = None
    manager_id: UUID | None = None

    def to_filters(self) -> ReportFilters:
        return ReportFilters(
            start_date=self.start_date,
            end_date=self.end_date,
            invoice_status=self.invoice_status,
            validation_outcome=self.validation_outcome,
            vendor_id=self.vendor_id,
            associate_id=self.associate_id,
            manager_id=self.manager_id,
        )


class NotificationListQueryParams(BaseModel):
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
