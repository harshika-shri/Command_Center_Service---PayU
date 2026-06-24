from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
    DashboardRepository,
)
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListItem,
    DashboardInvoiceListResponse,
    DashboardPaginationParams,
    DashboardSummaryResponse,
)


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
            total=counts.total,
        )

    async def list_ready_for_approval(
        self,
        pagination: DashboardPaginationParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.READY_FOR_APPROVAL,
            pagination=pagination,
            current_user=current_user,
        )

    async def list_needs_review(
        self,
        pagination: DashboardPaginationParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.NEEDS_REVIEW,
            pagination=pagination,
            current_user=current_user,
        )

    async def list_escalated(
        self,
        pagination: DashboardPaginationParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.ESCALATED,
            pagination=pagination,
            current_user=current_user,
        )

    async def list_ready_to_pay(
        self,
        pagination: DashboardPaginationParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.READY_TO_PAY,
            pagination=pagination,
            current_user=current_user,
        )

    async def list_rejected(
        self,
        pagination: DashboardPaginationParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.REJECTED,
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
        pagination: DashboardPaginationParams,
        current_user: User,
    ) -> DashboardInvoiceListResponse:
        rows, total_records = (
            await self.dashboard_repo.list_invoices_by_bucket(
                bucket=bucket,
                offset=pagination.offset,
                limit=pagination.page_size,
                extra_filter=self._ownership_filter_for_bucket(
                    current_user=current_user,
                    bucket=bucket,
                ),
            )
        )

        return DashboardInvoiceListResponse(
            items=[
                self._map_invoice_row(
                    row,
                )
                for row in rows
            ],
            page=pagination.page,
            page_size=pagination.page_size,
            total_records=total_records,
        )

    @staticmethod
    def _map_invoice_row(
        row: DashboardInvoiceRow,
    ) -> DashboardInvoiceListItem:
        return DashboardInvoiceListItem(
            invoice_id=row.invoice_id,
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
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
