from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Query

from src.schemas.list_query_schema import (
    InvoiceListQueryParams,
    NotificationListQueryParams,
    ReportFilterParams,
)


def invoice_list_query_params(
    search: str | None = Query(
        default=None,
    ),
    invoice_status: str | None = Query(
        default=None,
    ),
    validation_outcome: str | None = Query(
        default=None,
    ),
    vendor_id: UUID | None = Query(
        default=None,
    ),
    associate_id: UUID | None = Query(
        default=None,
    ),
    manager_id: UUID | None = Query(
        default=None,
    ),
    from_date: date | None = Query(
        default=None,
    ),
    to_date: date | None = Query(
        default=None,
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    sort_by: str = Query(
        default="created_at",
    ),
    sort_order: str = Query(
        default="desc",
    ),
) -> InvoiceListQueryParams:
    return InvoiceListQueryParams(
        search=search,
        invoice_status=invoice_status,
        validation_outcome=validation_outcome,
        vendor_id=vendor_id,
        associate_id=associate_id,
        manager_id=manager_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def notification_list_query_params(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> NotificationListQueryParams:
    return NotificationListQueryParams(
        page=page,
        page_size=page_size,
    )


def report_filter_params(
    start_date: date | None = Query(
        default=None,
    ),
    end_date: date | None = Query(
        default=None,
    ),
    invoice_status: str | None = Query(
        default=None,
    ),
    validation_outcome: str | None = Query(
        default=None,
    ),
    vendor_id: UUID | None = Query(
        default=None,
    ),
    associate_id: UUID | None = Query(
        default=None,
    ),
    manager_id: UUID | None = Query(
        default=None,
    ),
) -> ReportFilterParams:
    return ReportFilterParams(
        start_date=start_date,
        end_date=end_date,
        invoice_status=invoice_status,
        validation_outcome=validation_outcome,
        vendor_id=vendor_id,
        associate_id=associate_id,
        manager_id=manager_id,
    )
