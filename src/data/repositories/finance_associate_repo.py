from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, func, select

from src.core.services.ownership_resolver_service import (
    OwnershipResolverService,
)
from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
    dashboard_bucket_filter,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
)


@dataclass(frozen=True, slots=True)
class FinanceAssociateSummaryCounts:
    ready_for_approval: int
    needs_review: int
    escalated: int
    ready_to_pay: int
    rejected: int


class FinanceAssociateRepository(BaseRepository):
    async def get_owned_summary_counts(
        self,
        associate_id: UUID,
    ) -> FinanceAssociateSummaryCounts:
        counts = {
            bucket.value: await self._count_owned_bucket(
                associate_id,
                bucket,
            )
            for bucket in DashboardBucket
        }

        return FinanceAssociateSummaryCounts(
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
        )

    async def list_owned_invoices_by_bucket(
        self,
        *,
        associate_id: UUID,
        bucket: DashboardBucket,
        offset: int,
        limit: int,
    ) -> tuple[list[DashboardInvoiceRow], int]:
        bucket_filter = self._owned_bucket_filter(
            associate_id,
            bucket,
        )

        base_query = (
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_date,
                VendorMaster.vendor_name,
                Invoice.total_amount,
                Invoice.validation_outcome,
                Invoice.invoice_status,
                Invoice.rejection_reason,
                Invoice.escalated_to,
                Invoice.created_at,
            )
            .select_from(
                Invoice,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
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
                created_at=row.created_at,
            )
            for row in list_result.all()
        ]

        return items, total_records

    async def invoice_owned_by(
        self,
        *,
        associate_id: UUID,
        invoice_id: UUID,
    ) -> bool:
        ownership_resolver = OwnershipResolverService(
            self.session,
        )

        return await ownership_resolver.is_invoice_owned_by(
            invoice_id,
            associate_id,
        )

    async def _count_owned_bucket(
        self,
        associate_id: UUID,
        bucket: DashboardBucket,
    ) -> int:
        result = await self.execute(
            select(
                func.count(),
            )
            .select_from(
                Invoice,
            )
            .where(
                self._owned_bucket_filter(
                    associate_id,
                    bucket,
                ),
            ),
        )

        return int(
            result.scalar_one(),
        )

    @staticmethod
    def _owned_bucket_filter(
        associate_id: UUID,
        bucket: DashboardBucket,
    ):
        return and_(
            dashboard_bucket_filter(
                bucket,
            ),
            OwnershipResolverService._invoice_owned_by_filter(
                associate_id,
            ),
        )
