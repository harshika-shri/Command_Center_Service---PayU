from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.access_exc import (
    InvoiceAccessDeniedError,
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
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
)
from src.data.repositories.finance_associate_repo import (
    FinanceAssociateRepository,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListItem,
    DashboardInvoiceListResponse,
    DashboardPaginationParams,
    DashboardSummaryResponse,
)
from src.schemas.finance_associate_schema import (
    FinanceAssociateReviewResponse,
)


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
    ) -> FinanceAssociateReviewResponse:
        if not await self.ownership_service.is_associate_owner(
            associate_id=associate_id,
            invoice_id=invoice_id,
        ):
            raise InvoiceAccessDeniedError(
                "You do not have access to this invoice.",
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
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        rows, total_records = (
            await self.finance_associate_repo.list_invoices_by_bucket(
                associate_id=associate_id,
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
            due_date=row.due_date,
            vendor_name=row.vendor_name,
            total_amount=FinanceAssociateService._to_float(
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
