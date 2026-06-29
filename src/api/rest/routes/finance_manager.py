from uuid import UUID

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
from src.core.services.finance_manager_service import (
    FinanceManagerService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
)
from src.schemas.finance_manager_schema import (
    FinanceManagerReviewResponse,
    FinanceManagerSummaryResponse,
)
from src.schemas.list_query_schema import InvoiceListQueryParams

router = APIRouter(
    prefix="/finance-manager",
    tags=["Finance Manager"],
)

FINANCE_MANAGER_ROLES = (
    UserRole.FINANCE_MANAGER,
)


@router.get(
    "/dashboard/summary",
    response_model=FinanceManagerSummaryResponse,
)
async def get_finance_manager_summary(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
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
    "/invoices/my-escalated",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_my_escalated(
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
    )


@router.get(
    "/invoices/unassigned",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_unassigned(
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
    )


@router.get(
    "/invoices/my-claimed",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_my_claimed(
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
    )


@router.get(
    "/invoices/rejected",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_manager_rejected(
    query: InvoiceListQueryParams = Depends(
        invoice_list_query_params,
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
        query,
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
