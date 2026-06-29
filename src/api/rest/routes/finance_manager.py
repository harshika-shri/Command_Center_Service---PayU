from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.core.services.dashboard_charts_service import (
    DashboardChartsService,
)
from src.core.services.finance_manager_service import (
    FinanceManagerService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.dashboard_charts_schema import (
    ChartDataResponse,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardPaginationParams,
)
from src.schemas.finance_manager_schema import (
    FinanceManagerReviewResponse,
    FinanceManagerSummaryResponse,
)

router = APIRouter(
    prefix="/finance-manager",
    tags=["Finance Manager"],
)

FINANCE_MANAGER_ROLES = (
    UserRole.FINANCE_MANAGER,
)


def _pagination_params(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> DashboardPaginationParams:
    return DashboardPaginationParams(
        page=page,
        page_size=page_size,
    )


@router.get(
    "/dashboard/summary",
    response_model=FinanceManagerSummaryResponse,
)
async def get_finance_manager_summary(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> FinanceManagerSummaryResponse:
    service = FinanceManagerService(
        db,
    )

    return await service.get_summary(
        current_user.id,
    )


@router.get(
    "/dashboard/charts/status-distribution",
    response_model=ChartDataResponse,
)
async def get_manager_status_distribution_chart(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> ChartDataResponse:
    service = DashboardChartsService(
        db,
    )

    return await service.get_manager_status_distribution()


@router.get(
    "/dashboard/charts/team-performance",
    response_model=ChartDataResponse,
)
async def get_manager_team_performance_chart(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> ChartDataResponse:
    service = DashboardChartsService(
        db,
    )

    return await service.get_team_performance()


@router.get(
    "/dashboard/charts/validation-breakdown",
    response_model=ChartDataResponse,
)
async def get_manager_validation_breakdown_chart(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> ChartDataResponse:
    service = DashboardChartsService(
        db,
    )

    return await service.get_manager_validation_breakdown()


@router.get(
    "/dashboard/charts/pending-work-by-vendor",
    response_model=ChartDataResponse,
)
async def get_manager_pending_work_by_vendor_chart(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> ChartDataResponse:
    service = DashboardChartsService(
        db,
    )

    return await service.get_pending_work_by_vendor()


@router.get(
    "/invoices/my-escalated",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_my_escalated(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceManagerService(
        db,
    )

    return await service.list_my_escalated(
        current_user.id,
        pagination,
    )


@router.get(
    "/invoices/unassigned",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_unassigned(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceManagerService(
        db,
    )

    return await service.list_unassigned(
        current_user.id,
        pagination,
    )


@router.get(
    "/invoices/my-claimed",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_my_claimed(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceManagerService(
        db,
    )

    return await service.list_my_claimed(
        current_user.id,
        pagination,
    )


@router.get(
    "/invoices/rejected",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_rejected(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceManagerService(
        db,
    )

    return await service.list_rejected(
        current_user.id,
        pagination,
    )


@router.get(
    "/invoices/{invoice_id}/review",
    response_model=FinanceManagerReviewResponse,
)
async def get_finance_manager_invoice_review(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_MANAGER_ROLES,
        ),
    ),
) -> FinanceManagerReviewResponse:
    service = FinanceManagerService(
        db,
    )

    return await service.get_review(
        current_user.id,
        invoice_id,
    )
