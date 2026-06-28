from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dashboard_dependencies import (
    run_overdue_refresh_if_required,
)
from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.api.rest.list_query_dependencies import (
    invoice_list_query_params,
)
from src.core.services.dashboard_service import (
    DashboardService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardSummaryResponse,
)
from src.schemas.list_query_schema import InvoiceListQueryParams

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

DASHBOARD_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
    UserRole.FINANCE_MANAGER,
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
async def get_dashboard_summary(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
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
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
        current_user,
    )


@router.get(
    "/invoices/needs-review",
    response_model=DashboardInvoiceListResponse,
)
async def list_needs_review_invoices(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
        current_user,
    )


@router.get(
    "/invoices/escalated",
    response_model=DashboardInvoiceListResponse,
)
async def list_escalated_invoices(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
        current_user,
    )


@router.get(
    "/invoices/ready-to-pay",
    response_model=DashboardInvoiceListResponse,
)
async def list_ready_to_pay_invoices(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
        current_user,
    )


@router.get(
    "/invoices/rejected",
    response_model=DashboardInvoiceListResponse,
)
async def list_rejected_invoices(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
        current_user,
    )


@router.get(
    "/invoices/overdue",
    response_model=DashboardInvoiceListResponse,
)
async def list_overdue_invoices(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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

    return await service.list_overdue(
        query,
        current_user,
    )
