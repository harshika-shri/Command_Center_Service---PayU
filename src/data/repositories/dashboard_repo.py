from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, select

from src.core.query.search_filter_builder import (
    InvoiceListFilters,
    SearchFilterBuilder,
)
from src.core.query.sorting_helper import (
    SortingHelper,
)
from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
    dashboard_bucket_filter,
)
from src.data.models.postgres.invoice_extracted_vendor import (
    InvoiceExtractedVendor,
)
from src.data.models.postgres.invoice_extracted_vendor import InvoiceExtractedVendor
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class DashboardSummaryCounts:
    ready_for_approval: int
    needs_review: int
    escalated: int
    ready_to_pay: int
    rejected: int
    overdue: int
    total: int


@dataclass(frozen=True, slots=True)
class DashboardInvoiceRow:
    invoice_id: UUID
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None
    vendor_name: str | None
    total_amount: Decimal | None
    validation_outcome: str | None
    invoice_status: str | None
    rejection_reason: str | None
    escalated_to: UUID | None
    assigned_manager_id: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class InvoiceListQueryOptions:
    filters: InvoiceListFilters
    offset: int
    limit: int
    sort_by: str | None = "created_at"
    sort_order: str | None = "desc"


class DashboardRepository(BaseRepository):
    async def get_summary_counts(
        self,
        *,
        extra_filter: ColumnElement[bool] | None = None,
        bucket_extra_filters: dict[DashboardBucket, ColumnElement[bool]]
        | None = None,
    ) -> DashboardSummaryCounts:
        bucket_extra_filters = bucket_extra_filters or {}
        counts = {
            bucket.value: await self._count_bucket(
                bucket,
                extra_filter=bucket_extra_filters.get(
                    bucket,
                    extra_filter,
                ),
            )
            for bucket in DashboardBucket
        }

        return DashboardSummaryCounts(
            ready_for_approval=counts[
                DashboardBucket.READY_FOR_APPROVAL.value
            ],
            needs_review=counts[
                DashboardBucket.NEEDS_REVIEW.value
            ],
            escalated=counts[
                DashboardBucket.ESCALATED.value
            ],
            ready_to_pay=counts[
                DashboardBucket.READY_TO_PAY.value
            ],
            rejected=counts[
                DashboardBucket.REJECTED.value
            ],
            overdue=counts[
                DashboardBucket.OVERDUE.value
            ],
            total=sum(
                counts.values(),
            ),
        )

    async def list_invoices_by_bucket(
        self,
        *,
        bucket: DashboardBucket,
        query: InvoiceListQueryOptions,
        extra_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[DashboardInvoiceRow], int]:
        bucket_filter = dashboard_bucket_filter(
            bucket,
        )

        if extra_filter is not None:
            bucket_filter = and_(
                bucket_filter,
                extra_filter,
            )

        base_query = (
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_date,
                Invoice.due_date,
                func.coalesce(
                    VendorMaster.vendor_name,
                    InvoiceExtractedVendor.vendor_name,
                ).label(
                    "vendor_name",
                ),
                Invoice.total_amount,
                Invoice.validation_outcome,
                Invoice.invoice_status,
                Invoice.rejection_reason,
                Invoice.escalated_to,
                Invoice.assigned_manager_id,
                Invoice.created_at,
            )
            .select_from(
                Invoice,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .outerjoin(
                InvoiceExtractedVendor,
                InvoiceExtractedVendor.invoice_id == Invoice.id,
            )
            .where(
                bucket_filter,
            )
        )

        count_result = await self.execute(
            select(
                func.count(),
            )
            .select_from(
                Invoice,
            )
            .where(
                bucket_filter,
            ),
        )
        total_records = int(
            count_result.scalar_one(),
        )

        list_result = await self.execute(
            base_query.order_by(
                Invoice.created_at.desc(),
            )
            .offset(
                offset,
            )
            .limit(
                limit,
            ),
        )

        items = [
            DashboardInvoiceRow(
                invoice_id=row.id,
                invoice_number=row.invoice_number,
                invoice_date=row.invoice_date,
                due_date=row.due_date,
                vendor_name=row.vendor_name,
                total_amount=row.total_amount,
                validation_outcome=(
                    row.validation_outcome.value
                    if row.validation_outcome is not None
                    else None
                ),
                invoice_status=(
                    row.invoice_status.value
                    if row.invoice_status is not None
                    else None
                ),
                rejection_reason=row.rejection_reason,
                escalated_to=row.escalated_to,
                assigned_manager_id=row.assigned_manager_id,
                created_at=row.created_at,
            )
            for row in list_result.all()
        ]

        return items, total_records

        return await self._list_invoices(
            base_filter=bucket_filter,
            query=query,
            extra_filter=extra_filter,
        )

    async def list_invoices_by_custom_filter(
        self,
        *,
        bucket_filter: ColumnElement[bool],
        query: InvoiceListQueryOptions,
    ) -> tuple[list[DashboardInvoiceRow], int]:
        return await self._list_invoices(
            base_filter=bucket_filter,
            query=query,
        )

    async def count_by_custom_filter(
        self,
        *,
        bucket_filter: ColumnElement[bool],
        filters: InvoiceListFilters | None = None,
    ) -> int:
        return await self._count_with_filter(
            base_filter=bucket_filter,
            filters=filters or InvoiceListFilters(),
        )

    async def _list_invoices(
        self,
        *,
        base_filter: ColumnElement[bool],
        query: InvoiceListQueryOptions,
        extra_filter: ColumnElement[bool] | None = None,
    ) -> tuple[list[DashboardInvoiceRow], int]:
        combined_filter = self._combine_filters(
            base_filter=base_filter,
            filters=query.filters,
            extra_filter=extra_filter,
        )
        requires_vendor_join = SearchFilterBuilder.requires_vendor_join(
            query.filters,
            sort_by=query.sort_by,
        )

        count_query = select(
            func.count(
                func.distinct(
                    Invoice.id,
                ),
            ),
        ).select_from(
            Invoice,
        )

        if requires_vendor_join:
            count_query = count_query.outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )

        count_result = await self.execute(
            count_query.where(
                combined_filter,
            ),
        )
        total_records = int(
            count_result.scalar_one(),
        )

        list_query = (
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_date,
                Invoice.due_date,
                func.coalesce(
                    VendorMaster.vendor_name,
                    InvoiceExtractedVendor.vendor_name,
                ).label(
                    "vendor_name",
                ),

                func.coalesce(
                    VendorMaster.vendor_name,
                    InvoiceExtractedVendor.vendor_name,
                ).label("vendor_name"),

                Invoice.due_date,
                VendorMaster.vendor_name,
                Invoice.total_amount,
                Invoice.validation_outcome,
                Invoice.invoice_status,
                Invoice.rejection_reason,
                Invoice.escalated_to,
                Invoice.assigned_manager_id,
                Invoice.created_at,
            )
            .select_from(
                Invoice,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .outerjoin(
                InvoiceExtractedVendor,
                InvoiceExtractedVendor.invoice_id == Invoice.id,
            )
            .where(
                bucket_filter,
            )
        )

        count_result = await self.execute(
            select(
                func.count(),
            )
            .select_from(
                Invoice,
                Invoice.id == InvoiceExtractedVendor.invoice_id,
            )
            .where(
                combined_filter,
            )
            .order_by(
                SortingHelper.apply_sort(
                    sort_by=query.sort_by,
                    sort_order=query.sort_order,
                ),
            )
            .offset(
                query.offset,
            )
            .limit(
                query.limit,
            )
        )

        list_result = await self.execute(
            list_query,
        )

        items = [
            DashboardInvoiceRow(
                invoice_id=row.id,
                invoice_number=row.invoice_number,
                invoice_date=row.invoice_date,
                due_date=row.due_date,
                vendor_name=row.vendor_name,
                total_amount=row.total_amount,
                validation_outcome=(
                    row.validation_outcome.value
                    if row.validation_outcome is not None
                    else None
                ),
                invoice_status=(
                    row.invoice_status.value
                    if row.invoice_status is not None
                    else None
                ),
                rejection_reason=row.rejection_reason,
                escalated_to=row.escalated_to,
                assigned_manager_id=row.assigned_manager_id,
                created_at=row.created_at,
            )
            for row in list_result.all()
        ]

        return items, total_records

    async def _count_bucket(
        self,
        bucket: DashboardBucket,
        *,
        extra_filter: ColumnElement[bool] | None = None,
        filters: InvoiceListFilters | None = None,
    ) -> int:
        bucket_filter = dashboard_bucket_filter(
            bucket,
        )

        return await self._count_with_filter(
            base_filter=bucket_filter,
            filters=filters or InvoiceListFilters(),
            extra_filter=extra_filter,
        )

    async def _count_with_filter(
        self,
        *,
        base_filter: ColumnElement[bool],
        filters: InvoiceListFilters,
        extra_filter: ColumnElement[bool] | None = None,
    ) -> int:
        combined_filter = self._combine_filters(
            base_filter=base_filter,
            filters=filters,
            extra_filter=extra_filter,
        )
        requires_vendor_join = SearchFilterBuilder.requires_vendor_join(
            filters,
        )

        count_query = select(
            func.count(
                func.distinct(
                    Invoice.id,
                ),
            ),
        ).select_from(
            Invoice,
        )

        if requires_vendor_join:
            count_query = count_query.outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )

        result = await self.execute(
            count_query.where(
                combined_filter,
            ),
        )

        return int(
            result.scalar_one(),
        )

    @staticmethod
    def _combine_filters(
        *,
        base_filter: ColumnElement[bool],
        filters: InvoiceListFilters,
        extra_filter: ColumnElement[bool] | None = None,
    ) -> ColumnElement[bool]:
        conditions: list[ColumnElement[bool]] = [
            base_filter,
            SearchFilterBuilder.build_invoice_filters(
                filters,
            ),
        ]

        if extra_filter is not None:
            conditions.append(
                extra_filter,
            )

        return and_(
            *conditions,
        )

    @staticmethod
    def build_query_options(
        *,
        filters: InvoiceListFilters,
        offset: int,
        limit: int,
        sort_by: str | None,
        sort_order: str | None,
    ) -> InvoiceListQueryOptions:
        return InvoiceListQueryOptions(
            filters=filters,
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
