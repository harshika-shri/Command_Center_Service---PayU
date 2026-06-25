from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.core.workflow.invoice_workflow_buckets import (
    FinanceManagerBucket,
    finance_manager_bucket_filter,
)
from src.data.repositories.dashboard_repo import (
    DashboardInvoiceRow,
    DashboardRepository,
    InvoiceListQueryOptions,
)


@dataclass(frozen=True, slots=True)
class FinanceManagerSummaryCounts:
    my_escalated: int
    unassigned_queue: int
    my_claimed_unresolved: int
    rejected: int


class FinanceManagerRepository(DashboardRepository):
    async def get_summary_counts(
        self,
        manager_id: UUID,
    ) -> FinanceManagerSummaryCounts:
        counts = {
            bucket.value: await self.count_by_custom_filter(
                bucket_filter=finance_manager_bucket_filter(
                    bucket,
                    manager_id,
                ),
            )
            for bucket in FinanceManagerBucket
        }

        return FinanceManagerSummaryCounts(
            my_escalated=counts[
                FinanceManagerBucket.MY_ESCALATED.value
            ],
            unassigned_queue=counts[
                FinanceManagerBucket.UNASSIGNED_QUEUE.value
            ],
            my_claimed_unresolved=counts[
                FinanceManagerBucket.MY_CLAIMED_UNRESOLVED.value
            ],
            rejected=counts[
                FinanceManagerBucket.REJECTED.value
            ],
        )

    async def list_invoices_by_bucket(
        self,
        *,
        manager_id: UUID,
        bucket: FinanceManagerBucket,
        query: InvoiceListQueryOptions,
    ) -> tuple[list[DashboardInvoiceRow], int]:
        return await self.list_invoices_by_custom_filter(
            bucket_filter=finance_manager_bucket_filter(
                bucket,
                manager_id,
            ),
            query=query,
        )
