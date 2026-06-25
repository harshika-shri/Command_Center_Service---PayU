from __future__ import annotations

from uuid import UUID

from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
)
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
    DashboardRepository,
    DashboardSummaryCounts,
    InvoiceListQueryOptions,
)
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)


class FinanceAssociateRepository(DashboardRepository):
    async def get_summary_counts(
        self,
        associate_id: UUID,
    ) -> DashboardSummaryCounts:
        counts = {
            bucket.value: await self._count_bucket(
                bucket,
                associate_id=associate_id,
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
            total=sum(
                counts.values(),
            ),
        )

    async def list_invoices_by_bucket(
        self,
        *,
        associate_id: UUID,
        bucket: DashboardBucket,
        query: InvoiceListQueryOptions,
    ) -> tuple[list[DashboardInvoiceRow], int]:
        return await super().list_invoices_by_bucket(
            bucket=bucket,
            query=query,
            extra_filter=InvoiceOwnershipRepository.associate_ownership_filter(
                associate_id,
            ),
        )

    async def _count_bucket(
        self,
        bucket: DashboardBucket,
        *,
        associate_id: UUID | None = None,
    ) -> int:
        if associate_id is None:
            return await super()._count_bucket(
                bucket,
            )

        return await super()._count_bucket(
            bucket,
            extra_filter=InvoiceOwnershipRepository.associate_ownership_filter(
                associate_id,
            ),
        )
