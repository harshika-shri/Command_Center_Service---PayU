from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.repositories.reporting_repo import (
    ReportingRepository,
)
from src.schemas.list_query_schema import ReportFilterParams
from src.schemas.reporting_schema import (
    AssociateWorkloadItem,
    ManagerWorkloadItem,
    ReportPerformanceResponse,
    ReportSummaryResponse,
    VendorSummaryItem,
)


class ReportingService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.reporting_repo = ReportingRepository(
            session,
        )

    async def get_summary(
        self,
        filters: ReportFilterParams,
    ) -> ReportSummaryResponse:
        counts = await self.reporting_repo.get_summary_counts(
            filters=filters.to_filters(),
        )

        return ReportSummaryResponse(
            total_invoices=counts.total_invoices,
            under_review=counts.under_review,
            ready_to_pay=counts.ready_to_pay,
            rejected=counts.rejected,
            escalated=counts.escalated,
        )

    async def get_performance(
        self,
        filters: ReportFilterParams,
    ) -> ReportPerformanceResponse:
        metrics = await self.reporting_repo.get_performance_metrics(
            filters=filters.to_filters(),
        )

        return ReportPerformanceResponse(
            avg_approval_time_hours=metrics.avg_approval_time_hours,
            avg_rejection_time_hours=metrics.avg_rejection_time_hours,
        )

    async def get_vendor_summary(
        self,
        filters: ReportFilterParams,
    ) -> list[VendorSummaryItem]:
        rows = await self.reporting_repo.get_vendor_summary(
            filters=filters.to_filters(),
        )

        return [
            VendorSummaryItem(
                vendor_name=row.vendor_name,
                invoice_count=row.invoice_count,
            )
            for row in rows
        ]

    async def get_associate_workload(
        self,
        filters: ReportFilterParams,
    ) -> list[AssociateWorkloadItem]:
        rows = await self.reporting_repo.get_associate_workload(
            filters=filters.to_filters(),
        )

        return [
            AssociateWorkloadItem(
                associate_name=row.associate_name,
                under_review=row.under_review,
                approved=row.approved,
                rejected=row.rejected,
                escalated=row.escalated,
            )
            for row in rows
        ]

    async def get_manager_workload(
        self,
        filters: ReportFilterParams,
    ) -> list[ManagerWorkloadItem]:
        rows = await self.reporting_repo.get_manager_workload(
            filters=filters.to_filters(),
        )

        return [
            ManagerWorkloadItem(
                manager_name=row.manager_name,
                escalated=row.escalated,
                claimed_unresolved=row.claimed_unresolved,
                approved=row.approved,
                rejected=row.rejected,
            )
            for row in rows
        ]
