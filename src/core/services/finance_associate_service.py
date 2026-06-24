from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.dashboard_service import (
    DashboardService,
)
from src.core.services.invoice_review_service import (
    InvoiceReviewService,
)
from src.core.services.ownership_resolver_service import (
    OwnershipResolverService,
)
from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
)
from src.data.repositories.finance_associate_repo import (
    FinanceAssociateRepository,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardPaginationParams,
)
from src.schemas.finance_associate_schema import (
    FinanceAssociateSummaryResponse,
)
from src.schemas.invoice_review_schema import (
    InvoiceReviewResponse,
)


class FinanceAssociateService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.finance_associate_repo = FinanceAssociateRepository(
            session,
        )
        self.ownership_resolver = OwnershipResolverService(
            session,
        )
        self.invoice_review_service = InvoiceReviewService(
            session,
        )

    async def get_summary(
        self,
        associate_id: UUID,
    ) -> FinanceAssociateSummaryResponse:
        counts = (
            await self.finance_associate_repo.get_owned_summary_counts(
                associate_id,
            )
        )

        return FinanceAssociateSummaryResponse(
            ready_for_approval=counts.ready_for_approval,
            needs_review=counts.needs_review,
            escalated=counts.escalated,
            ready_to_pay=counts.ready_to_pay,
            rejected=counts.rejected,
        )

    async def list_ready_for_approval(
        self,
        associate_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.READY_FOR_APPROVAL,
            pagination=pagination,
        )

    async def list_needs_review(
        self,
        associate_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.NEEDS_REVIEW,
            pagination=pagination,
        )

    async def list_ready_to_pay(
        self,
        associate_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.READY_TO_PAY,
            pagination=pagination,
        )

    async def list_rejected(
        self,
        associate_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.REJECTED,
            pagination=pagination,
        )

    async def get_review(
        self,
        associate_id: UUID,
        invoice_id: UUID,
    ) -> InvoiceReviewResponse:
        await self.ownership_resolver.ensure_invoice_owned_by(
            invoice_id,
            associate_id,
        )

        return await self.invoice_review_service.get_review(
            invoice_id,
        )

    async def _list_by_bucket(
        self,
        *,
        associate_id: UUID,
        bucket: DashboardBucket,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        rows, total_records = (
            await self.finance_associate_repo.list_owned_invoices_by_bucket(
                associate_id=associate_id,
                bucket=bucket,
                offset=pagination.offset,
                limit=pagination.page_size,
            )
        )

        return DashboardInvoiceListResponse(
            items=[
                DashboardService._map_invoice_row(
                    row,
                )
                for row in rows
            ],
            page=pagination.page,
            page_size=pagination.page_size,
            total_records=total_records,
        )
