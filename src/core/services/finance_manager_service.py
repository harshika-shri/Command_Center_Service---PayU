from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.invoice_ownership_service import (
    InvoiceOwnershipService,
)
from src.core.services.invoice_review_service import (
    InvoiceReviewService,
)
from src.core.workflow.invoice_workflow_buckets import (
    FinanceManagerBucket,
)
from src.data.models.postgres.enums import UserRole
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
)
from src.data.repositories.finance_manager_repo import (
    FinanceManagerRepository,
)
from src.data.repositories.invoice_communication_repo import (
    InvoiceCommunicationRepository,
)
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListItem,
    DashboardInvoiceListResponse,
    DashboardPaginationParams,
)
from src.schemas.finance_manager_schema import (
    CommunicationTimelineItem,
    DisputeHistoryItem,
    FinanceManagerReviewResponse,
    FinanceManagerSummaryResponse,
    InvoiceOwnershipDetails,
)


class FinanceManagerService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.finance_manager_repo = FinanceManagerRepository(
            session,
        )
        self.review_service = InvoiceReviewService(
            session,
        )
        self.ownership_service = InvoiceOwnershipService(
            session,
        )
        self.ownership_repo = InvoiceOwnershipRepository(
            session,
        )
        self.communication_repo = InvoiceCommunicationRepository(
            session,
        )

    async def get_summary(
        self,
        manager_id: UUID,
    ) -> FinanceManagerSummaryResponse:
        counts = await self.finance_manager_repo.get_summary_counts(
            manager_id,
        )

        return FinanceManagerSummaryResponse(
            my_escalated=counts.my_escalated,
            unassigned_queue=counts.unassigned_queue,
            my_claimed_unresolved=counts.my_claimed_unresolved,
            rejected=counts.rejected,
        )

    async def list_my_escalated(
        self,
        manager_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            manager_id=manager_id,
            bucket=FinanceManagerBucket.MY_ESCALATED,
            pagination=pagination,
        )

    async def list_unassigned(
        self,
        manager_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            manager_id=manager_id,
            bucket=FinanceManagerBucket.UNASSIGNED_QUEUE,
            pagination=pagination,
        )

    async def list_my_claimed(
        self,
        manager_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            manager_id=manager_id,
            bucket=FinanceManagerBucket.MY_CLAIMED_UNRESOLVED,
            pagination=pagination,
        )

    async def list_rejected(
        self,
        manager_id: UUID,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        return await self._list_by_bucket(
            manager_id=manager_id,
            bucket=FinanceManagerBucket.REJECTED,
            pagination=pagination,
        )

    async def get_review(
        self,
        manager_id: UUID,
        invoice_id: UUID,
    ) -> FinanceManagerReviewResponse:
        ownership_details = await self.ownership_repo.get_ownership_details(
            invoice_id,
        )

        if ownership_details is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        review = await self.review_service.get_review(
            invoice_id,
        )
        disputes = await self.communication_repo.list_disputes_by_invoice(
            invoice_id,
        )
        communications = (
            await self.communication_repo.list_communication_history(
                invoice_id,
            )
        )
        can_take_action = await self.ownership_service.can_take_action(
            user_id=manager_id,
            user_role=UserRole.FINANCE_MANAGER,
            invoice_id=invoice_id,
        )
        can_take_ownership = await self.ownership_service.is_unassigned(
            invoice_id,
        )

        return FinanceManagerReviewResponse(
            review=review,
            ownership=InvoiceOwnershipDetails(
                associate_owner_id=ownership_details.associate_owner_id,
                associate_owner_name=ownership_details.associate_owner_name,
                associate_owner_email=ownership_details.associate_owner_email,
                assigned_manager_id=ownership_details.assigned_manager_id,
                assigned_manager_name=ownership_details.assigned_manager_name,
                assigned_manager_email=ownership_details.assigned_manager_email,
                escalated_by_id=ownership_details.escalated_by_id,
                escalated_by_name=ownership_details.escalated_by_name,
                escalated_by_email=ownership_details.escalated_by_email,
                assigned_at=ownership_details.assigned_at,
            ),
            disputes=[
                DisputeHistoryItem(
                    dispute_id=dispute.dispute_id,
                    reason_category=dispute.reason_category,
                    status=dispute.status,
                    description=dispute.description,
                    raised_by_id=dispute.raised_by_id,
                    raised_by_name=dispute.raised_by_name,
                    created_at=dispute.created_at,
                )
                for dispute in disputes
            ],
            communication_timeline=[
                CommunicationTimelineItem(
                    communication_id=communication.communication_id,
                    dispute_id=communication.dispute_id,
                    communication_type=communication.communication_type,
                    reason_category=communication.reason_category,
                    subject=communication.subject,
                    body=communication.body,
                    recipient_email=communication.recipient_email,
                    status=communication.status,
                    sent_at=communication.sent_at,
                    sent_by_id=communication.sent_by_id,
                    sent_by_name=communication.sent_by_name,
                    created_at=communication.created_at,
                )
                for communication in communications
            ],
            can_take_action=can_take_action,
            can_take_ownership=can_take_ownership,
        )

    async def _list_by_bucket(
        self,
        *,
        manager_id: UUID,
        bucket: FinanceManagerBucket,
        pagination: DashboardPaginationParams,
    ) -> DashboardInvoiceListResponse:
        rows, total_records = (
            await self.finance_manager_repo.list_invoices_by_bucket(
                manager_id=manager_id,
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
            total_amount=FinanceManagerService._to_float(
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
