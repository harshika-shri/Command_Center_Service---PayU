from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.api.rest.list_query_dependencies import (
    report_filter_params,
)
from src.core.services.reporting_service import (
    ReportingService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.list_query_schema import ReportFilterParams
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


@router.get(
    "/summary",
    response_model=ReportSummaryResponse,
)
async def get_report_summary(
    filters: ReportFilterParams = Depends(
        report_filter_params,
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
    service = ReportingService(
        db,
    )

    return await service.get_summary(
        filters,
    )


@router.get(
    "/performance",
    response_model=ReportPerformanceResponse,
)
async def get_report_performance(
    filters: ReportFilterParams = Depends(
        report_filter_params,
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
    service = ReportingService(
        db,
    )

    return await service.get_performance(
        filters,
    )


@router.get(
    "/vendors",
    response_model=list[VendorSummaryItem],
)
async def get_report_vendors(
    filters: ReportFilterParams = Depends(
        report_filter_params,
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
    service = ReportingService(
        db,
    )

    return await service.get_vendor_summary(
        filters,
    )


@router.get(
    "/associates",
    response_model=list[AssociateWorkloadItem],
)
async def get_report_associates(
    filters: ReportFilterParams = Depends(
        report_filter_params,
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
    service = ReportingService(
        db,
    )

    return await service.get_associate_workload(
        filters,
    )


@router.get(
    "/managers",
    response_model=list[ManagerWorkloadItem],
)
async def get_report_managers(
    filters: ReportFilterParams = Depends(
        report_filter_params,
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
    service = ReportingService(
        db,
    )

    return await service.get_manager_workload(
        filters,
    )
