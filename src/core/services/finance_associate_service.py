from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.authorization_service import (
    AuthorizationService,
)
from src.core.services.dashboard_service import (
    DashboardService,
)
from src.core.services.invoice_ownership_service import (
    InvoiceOwnershipService,
)
from src.core.services.invoice_review_service import (
    InvoiceReviewService,
)
from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
)
from src.data.models.postgres.enums import UserRole
from src.data.repositories.finance_associate_repo import (
    FinanceAssociateRepository,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardSummaryResponse,
)
from src.schemas.finance_associate_schema import (
    FinanceAssociateReviewResponse,
)
from src.schemas.list_query_schema import InvoiceListQueryParams


class FinanceAssociateService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.finance_associate_repo = FinanceAssociateRepository(
            session,
        )
        self.review_service = InvoiceReviewService(
            session,
        )
        self.ownership_service = InvoiceOwnershipService(
            session,
        )
        self.authorization_service = AuthorizationService(
            session,
        )

    async def get_summary(
        self,
        associate_id: UUID,
    ) -> DashboardSummaryResponse:
        counts = await self.finance_associate_repo.get_summary_counts(
            associate_id,
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
        associate_id: UUID,
        query: InvoiceListQueryParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.READY_FOR_APPROVAL,
            query=query,
        )

    async def list_needs_review(
        self,
        associate_id: UUID,
        query: InvoiceListQueryParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.NEEDS_REVIEW,
            query=query,
        )

    async def list_ready_to_pay(
        self,
        associate_id: UUID,
        query: InvoiceListQueryParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.READY_TO_PAY,
            query=query,
        )

    async def list_rejected(
        self,
        associate_id: UUID,
        query: InvoiceListQueryParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            associate_id=associate_id,
            bucket=DashboardBucket.REJECTED,
            query=query,
        )

    async def get_review(
        self,
        associate_id: UUID,
        invoice_id: UUID,
    ) -> FinanceAssociateReviewResponse:
        await self.authorization_service.ensure_can_view_invoice(
            user_id=associate_id,
            user_role=UserRole.FINANCE_ASSOCIATE,
            invoice_id=invoice_id,
        )

        review = await self.review_service.get_review(
            invoice_id,
        )
        can_take_action = await self.ownership_service.can_take_action(
            user_id=associate_id,
            user_role=UserRole.FINANCE_ASSOCIATE,
            invoice_id=invoice_id,
        )

        return FinanceAssociateReviewResponse(
            review=review,
            can_take_action=can_take_action,
        )

    async def _list_by_bucket(
        self,
        *,
        associate_id: UUID,
        bucket: DashboardBucket,
        query: InvoiceListQueryParams,
    ) -> DashboardInvoiceListResponse:
        list_query = self.finance_associate_repo.build_query_options(
            filters=query.to_filters(),
            offset=query.offset,
            limit=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        rows, total_records = (
            await self.finance_associate_repo.list_invoices_by_bucket(
                associate_id=associate_id,
                bucket=bucket,
                query=list_query,
            )
        )

        return DashboardService._build_list_response(
            rows=rows,
            total_records=total_records,
            query=query,
        )
