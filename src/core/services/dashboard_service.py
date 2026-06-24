from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
)
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
    DashboardRepository,
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

    async def get_summary(self) -> DashboardSummaryResponse:
        counts = await self.dashboard_repo.get_summary_counts()

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
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.READY_FOR_APPROVAL,
            pagination=pagination,
        )

    async def list_needs_review(
        self,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.NEEDS_REVIEW,
            pagination=pagination,
        )

    async def list_escalated(
        self,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.ESCALATED,
            pagination=pagination,
        )

    async def list_ready_to_pay(
        self,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.READY_TO_PAY,
            pagination=pagination,
        )

    async def list_rejected(
        self,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            bucket=DashboardBucket.REJECTED,
            pagination=pagination,
        )

    async def _list_by_bucket(
        self,
        *,
        bucket: DashboardBucket,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        rows, total_records = (
            await self.dashboard_repo.list_invoices_by_bucket(
                bucket=bucket,
                offset=pagination.offset,
                limit=pagination.page_size,
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
