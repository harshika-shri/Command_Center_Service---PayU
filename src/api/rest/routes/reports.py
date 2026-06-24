from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.core.services.reporting_service import (
    ReportingService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.reporting_schema import (
    AssociateWorkloadItem,
    ManagerWorkloadItem,
    ReportPerformanceResponse,
    ReportSummaryResponse,
    VendorSummaryItem,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)

REPORTING_ROLES = (
    UserRole.FINANCE_MANAGER,
)


def _report_date_filters(
    start_date: date | None = Query(
        default=None,
    ),
    end_date: date | None = Query(
        default=None,
    ),
) -> tuple[date | None, date | None]:
    return start_date, end_date


@router.get(
    "/summary",
    response_model=ReportSummaryResponse,
)
async def get_report_summary(
    date_filters: tuple[date | None, date | None] = Depends(
        _report_date_filters,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *REPORTING_ROLES,
        ),
    ),
) -> ReportSummaryResponse:
    start_date, end_date = date_filters
    service = ReportingService(
        db,
    )

    return await service.get_summary(
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/performance",
    response_model=ReportPerformanceResponse,
)
async def get_report_performance(
    date_filters: tuple[date | None, date | None] = Depends(
        _report_date_filters,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *REPORTING_ROLES,
        ),
    ),
) -> ReportPerformanceResponse:
    start_date, end_date = date_filters
    service = ReportingService(
        db,
    )

    return await service.get_performance(
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/vendors",
    response_model=list[VendorSummaryItem],
)
async def get_report_vendors(
    date_filters: tuple[date | None, date | None] = Depends(
        _report_date_filters,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *REPORTING_ROLES,
        ),
    ),
) -> list[VendorSummaryItem]:
    start_date, end_date = date_filters
    service = ReportingService(
        db,
    )

    return await service.get_vendor_summary(
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/associates",
    response_model=list[AssociateWorkloadItem],
)
async def get_report_associates(
    date_filters: tuple[date | None, date | None] = Depends(
        _report_date_filters,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *REPORTING_ROLES,
        ),
    ),
) -> list[AssociateWorkloadItem]:
    start_date, end_date = date_filters
    service = ReportingService(
        db,
    )

    return await service.get_associate_workload(
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/managers",
    response_model=list[ManagerWorkloadItem],
)
async def get_report_managers(
    date_filters: tuple[date | None, date | None] = Depends(
        _report_date_filters,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *REPORTING_ROLES,
        ),
    ),
) -> list[ManagerWorkloadItem]:
    start_date, end_date = date_filters
    service = ReportingService(
        db,
    )

    return await service.get_manager_workload(
        start_date=start_date,
        end_date=end_date,
    )
