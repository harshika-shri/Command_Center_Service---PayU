from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.query.pagination_helper import PaginationHelper
from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
    DashboardRepository,
    InvoiceListQueryOptions,
)
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListItem,
    DashboardInvoiceListResponse,
    DashboardSummaryResponse,
)
from src.schemas.list_query_schema import InvoiceListQueryParams


class DashboardService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.dashboard_repo = DashboardRepository(
            session,
        )

    async def get_summary(
        self,
        current_user: User,
    ) -> DashboardSummaryResponse:
        counts = await self.dashboard_repo.get_summary_counts(
            bucket_extra_filters=self._bucket_filters_for_user(
                current_user,
            ),
        )

        return DashboardSummaryResponse(
            ready_for_approval=counts.ready_for_approval,
            needs_review=counts.needs_review,
            escalated=counts.escalated,
            ready_to_pay=counts.ready_to_pay,
            rejected=counts.rejected,
            overdue=counts.overdue,
            total=counts.total,
        )

    async def list_ready_for_approval(
        self,
        query: InvoiceListQueryParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.READY_FOR_APPROVAL,
            query=query,
            current_user=current_user,
        )

    async def list_needs_review(
        self,
        query: InvoiceListQueryParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.NEEDS_REVIEW,
            query=query,
            current_user=current_user,
        )

    async def list_escalated(
        self,
        query: InvoiceListQueryParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.ESCALATED,
            query=query,
            current_user=current_user,
        )

    async def list_ready_to_pay(
        self,
        query: InvoiceListQueryParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.READY_TO_PAY,
            query=query,
            current_user=current_user,
        )

    async def list_rejected(
        self,
        query: InvoiceListQueryParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.REJECTED,
            query=query,
            current_user=current_user,
        )

    async def list_overdue(
        self,
        query: InvoiceListQueryParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.OVERDUE,
            query=query,
            current_user=current_user,
        )

    async def list_overdue(
        self,
        pagination: DashboardPaginationParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.OVERDUE,
            pagination=pagination,
            current_user=current_user,
        )

    def _bucket_filters_for_user(
        self,
        current_user: User,
    ) -> dict[DashboardBucket, ColumnElement[bool] | None]:
        if current_user.role == UserRole.FINANCE_ASSOCIATE:
            associate_filter = (
                InvoiceOwnershipRepository.associate_ownership_filter(
                    current_user.id,
                )
            )

            return {
                bucket: associate_filter
                for bucket in DashboardBucket
            }

        if current_user.role == UserRole.FINANCE_MANAGER:
            manager_escalated_filter = (
                InvoiceOwnershipRepository.manager_assigned_filter(
                    current_user.id,
                )
            )

            return {
                DashboardBucket.ESCALATED: manager_escalated_filter,
            }

        return {}

    def _ownership_filter_for_bucket(
        self,
        *,
        current_user: User,
        bucket: DashboardBucket,
    ) -> ColumnElement[bool] | None:
        return self._bucket_filters_for_user(
            current_user,
        ).get(
            bucket,
        )

    async def _list_by_bucket(
        self,
        *,
        bucket: DashboardBucket,
        query: InvoiceListQueryParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        list_query = self.dashboard_repo.build_query_options(
            filters=query.to_filters(),
            offset=query.offset,
            limit=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        rows, total_records = (
            await self.dashboard_repo.list_invoices_by_bucket(
                bucket=bucket,
                query=list_query,
                extra_filter=self._ownership_filter_for_bucket(
                    current_user=current_user,
                    bucket=bucket,
                ),
            )
        )

        return self._build_list_response(
            rows=rows,
            total_records=total_records,
            query=query,
        )

    @staticmethod
    def _build_list_response(
        *,
        rows: list[DashboardInvoiceRow],
        total_records: int,
        query: InvoiceListQueryParams,
    ) -> DashboardInvoiceListResponse:
        metadata = PaginationHelper.build_metadata(
            total_records=total_records,
            current_page=query.page,
            page_size=query.page_size,
        )

        return DashboardInvoiceListResponse(
            items=[
                DashboardService._map_invoice_row(
                    row,
                )
                for row in rows
            ],
            total_records=metadata.total_records,
            total_pages=metadata.total_pages,
            current_page=metadata.current_page,
            page_size=metadata.page_size,
            page=metadata.current_page,
        )

    @staticmethod
    def _map_invoice_row(
        row: DashboardInvoiceRow,
    ) -> DashboardInvoiceListItem:
        return DashboardInvoiceListItem(
            invoice_id=row.invoice_id,
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
            due_date=row.due_date,
            vendor_name=row.vendor_name,
            total_amount=DashboardService._to_float(
                row.total_amount,
            ),
            validation_outcome=row.validation_outcome,
            invoice_status=row.invoice_status,
            rejection_reason=row.rejection_reason,
            escalated_to=row.escalated_to,
            assigned_manager_id=row.assigned_manager_id,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_float(
        amount: Decimal | None,
    ) -> float | None:
        if amount is None:
            return None

        return float(
            amount,
        )
