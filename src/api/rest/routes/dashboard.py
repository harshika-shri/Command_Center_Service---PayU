from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.core.services.dashboard_service import (
    DashboardService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardPaginationParams,
    DashboardSummaryResponse,
)

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

DASHBOARD_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
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
    sort_by: str | None = Query(
        default=None,
    ),
    sort_order: str | None = Query(
        default=None,
    ),
) -> DashboardPaginationParams:
    return DashboardPaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
async def get_dashboard_summary(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *DASHBOARD_ROLES,
        ),
    ),
) -> DashboardSummaryResponse:
    service = DashboardService(
        db,
    )

    return await service.get_summary(
        current_user,
    )


@router.get(
    "/invoices/ready-for-approval",
    response_model=DashboardInvoiceListResponse,
)
async def list_ready_for_approval_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *DASHBOARD_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = DashboardService(
        db,
    )

    return await service.list_ready_for_approval(
        pagination,
        current_user,
    )


@router.get(
    "/invoices/needs-review",
    response_model=DashboardInvoiceListResponse,
)
async def list_needs_review_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *DASHBOARD_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = DashboardService(
        db,
    )

    return await service.list_needs_review(
        pagination,
        current_user,
    )


@router.get(
    "/invoices/escalated",
    response_model=DashboardInvoiceListResponse,
)
async def list_escalated_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *DASHBOARD_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = DashboardService(
        db,
    )

    return await service.list_escalated(
        pagination,
        current_user,
    )


@router.get(
    "/invoices/ready-to-pay",
    response_model=DashboardInvoiceListResponse,
)
async def list_ready_to_pay_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *DASHBOARD_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = DashboardService(
        db,
    )

    return await service.list_ready_to_pay(
        pagination,
        current_user,
    )


@router.get(
    "/invoices/rejected",
    response_model=DashboardInvoiceListResponse,
)
async def list_rejected_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *DASHBOARD_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = DashboardService(
        db,
    )

    return await service.list_rejected(
        pagination,
        current_user,
    )
