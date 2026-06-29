from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.constants.report_constants import (
    ReportAssociateViewMode,
    ReportInvoiceStatus,
    ReportIssueSeverity,
    ReportOverdueFilter,
    ReportValidationNode,
    ReportValidationOutcome,
)


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


class ReportPaginationParams(BaseModel):
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


class InvoiceReportQueryParams(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    invoice_status: ReportInvoiceStatus | None = None
    validation_outcome: ReportValidationOutcome | None = None
    vendor_id: UUID | None = None
    finance_associate_id: UUID | None = None
    validation_node: ReportValidationNode | None = None
    issue_severity: ReportIssueSeverity | None = None
    overdue: ReportOverdueFilter = ReportOverdueFilter.ALL
    po_number: str | None = None
    invoice_number: str | None = None
    search: str | None = None
    sort_by: str = "invoice_date"
    sort_dir: str = "desc"
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

    @property
    def from_date_utc(self) -> datetime | None:
        if self.from_date is None:
            return None

        return to_utc_start(
            self.from_date,
        )

    @property
    def to_date_utc(self) -> datetime | None:
        if self.to_date is None:
            return None

        return to_utc_end_exclusive(
            self.to_date,
        )


class FinanceAssociateReportQueryParams(BaseModel):
    from_date: date | None = None
    to_date: date | None = None
    finance_associate_id: UUID | None = None
    view_mode: ReportAssociateViewMode = ReportAssociateViewMode.OVERALL
    search: str | None = None
    sort_by: str = "associate_name"
    sort_dir: str = "asc"
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

    @property
    def from_date_utc(self) -> datetime | None:
        if self.from_date is None:
            return None

        return to_utc_start(
            self.from_date,
        )

    @property
    def to_date_utc(self) -> datetime | None:
        if self.to_date is None:
            return None

        return to_utc_end_exclusive(
            self.to_date,
        )


class VendorOption(BaseModel):
    id: UUID
    vendor_name: str


class FinanceAssociateOption(BaseModel):
    id: UUID
    name: str


class ReportFilterOptionsResponse(BaseModel):
    vendors: list[VendorOption]
    finance_associates: list[FinanceAssociateOption]
    invoice_statuses: list[dict[str, str]]
    validation_outcomes: list[dict[str, str]]
    validation_nodes: list[dict[str, str]]
    issue_severities: list[dict[str, str]]
    overdue_options: list[dict[str, str]]


class InvoiceReportItem(BaseModel):
    invoice_id: UUID
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None
    invoice_status: str | None
    validation_outcome: str | None
    total_amount: float | None
    tax_amount: float | None
    currency: str | None
    vendor_name: str | None
    vendor_gstin: str | None
    vendor_email: str | None
    company_name: str | None
    po_number: str | None
    po_date: date | None
    po_status: str | None
    assigned_finance_associate: str | None
    assigned_finance_manager: str | None
    resolution_type: str | None
    validation_issue_count: int
    highest_issue_severity: str | None
    workflow_status: str | None
    approved_by: str | None
    rejected_by: str | None
    escalated_by: str | None


class InvoiceReportListResponse(BaseModel):
    items: list[InvoiceReportItem]
    page: int
    page_size: int
    total_records: int


class FinanceAssociatePerformanceItem(BaseModel):
    associate_id: UUID
    associate_name: str
    report_date: date | None = None
    total_assigned: int
    approved: int
    rejected: int
    needs_review: int
    ready_for_approval: int
    ready_to_pay: int
    overdue: int
    escalated: int
    resolved_count: int
    recovered_count: int
    approval_rate: float
    rejection_rate: float


class FinanceAssociatePerformanceListResponse(BaseModel):
    items: list[FinanceAssociatePerformanceItem]
    page: int
    page_size: int
    total_records: int
