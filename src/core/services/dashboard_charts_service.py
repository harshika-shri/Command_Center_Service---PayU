from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.repositories.dashboard_charts_repo import (
    DashboardChartsRepository,
)
from src.schemas.dashboard_charts_schema import ChartDataResponse


class DashboardChartsService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.charts_repo = DashboardChartsRepository(
            session,
        )

    async def get_associate_status_distribution(
        self,
        associate_id: UUID,
    ) -> ChartDataResponse:
        labels, values = await self.charts_repo.get_status_distribution(
            associate_id=associate_id,
        )
        return ChartDataResponse(
            labels=labels,
            values=values,
        )

    async def get_associate_validation_breakdown(
        self,
        associate_id: UUID,
    ) -> ChartDataResponse:
        labels, values = await self.charts_repo.get_validation_breakdown(
            associate_id=associate_id,
        )
        return ChartDataResponse(
            labels=labels,
            values=values,
        )

    async def get_associate_processing_trend(
        self,
        associate_id: UUID,
    ) -> ChartDataResponse:
        labels, values = await self.charts_repo.get_processing_trend(
            associate_id,
        )
        return ChartDataResponse(
            labels=labels,
            values=values,
        )

    async def get_manager_status_distribution(
        self,
    ) -> ChartDataResponse:
        labels, values = await self.charts_repo.get_status_distribution()
        return ChartDataResponse(
            labels=labels,
            values=values,
        )

    async def get_manager_team_performance(
        self,
    ) -> ChartDataResponse:
        labels, values = await self.charts_repo.get_team_performance()
        return ChartDataResponse(
            labels=labels,
            values=values,
        )

    async def get_manager_validation_breakdown(
        self,
    ) -> ChartDataResponse:
        labels, values = await self.charts_repo.get_validation_breakdown()
        return ChartDataResponse(
            labels=labels,
            values=values,
        )

    async def get_manager_pending_work_by_vendor(
        self,
    ) -> ChartDataResponse:
        labels, values = await self.charts_repo.get_pending_work_by_vendor()
        return ChartDataResponse(
            labels=labels,
            values=values,
        )
