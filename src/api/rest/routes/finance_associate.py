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
from src.core.services.dashboard_charts_service import (
    DashboardChartsService,
)
from src.core.services.finance_associate_service import (
    FinanceAssociateService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.dashboard_charts_schema import (
    ChartDataResponse,
)
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
)
from src.schemas.finance_associate_schema import (
    FinanceAssociateDashboardSummaryResponse,
    FinanceAssociateReviewResponse,
)
from src.schemas.list_query_schema import InvoiceListQueryParams

router = APIRouter(
    prefix="/finance-associate",
    tags=["Finance Associate"],
)

FINANCE_ASSOCIATE_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
)


@router.get(
    "/dashboard/summary",
    response_model=FinanceAssociateDashboardSummaryResponse,
)
async def get_finance_associate_summary(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> FinanceAssociateDashboardSummaryResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.get_summary(
        current_user.id,
    )


@router.get(
    "/dashboard/charts/status-distribution",
    response_model=ChartDataResponse,
)
async def get_associate_status_distribution(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> ChartDataResponse:
    service = DashboardChartsService(
        db,
    )

    return await service.get_associate_status_distribution(
        current_user.id,
    )


@router.get(
    "/dashboard/charts/validation-breakdown",
    response_model=ChartDataResponse,
)
async def get_associate_validation_breakdown(
    _: None = Depends(
        run_overdue_refresh_if_required,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> ChartDataResponse:
    service = DashboardChartsService(
        db,
    )

    return await service.get_associate_validation_breakdown(
        current_user.id,
    )


@router.get(
    "/dashboard/charts/processing-trend",
    response_model=ChartDataResponse,
)
async def get_associate_processing_trend(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> ChartDataResponse:
    service = DashboardChartsService(
        db,
    )

    return await service.get_associate_processing_trend(
        current_user.id,
    )


@router.get(
    "/invoices/ready-for-approval",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_ready_for_approval(
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
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.list_ready_for_approval(
        current_user.id,
        query,
    )


@router.get(
    "/invoices/needs-review",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_needs_review(
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
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.list_needs_review(
        current_user.id,
        query,
    )


@router.get(
    "/invoices/ready-to-pay",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_ready_to_pay(
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
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.list_ready_to_pay(
        current_user.id,
        query,
    )


@router.get(
    "/invoices/rejected",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_rejected(
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
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> DashboardInvoiceListResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.list_rejected(
        current_user.id,
        query,
    )


@router.get(
    "/invoices/{invoice_id}/review",
    response_model=FinanceAssociateReviewResponse,
)
async def get_finance_associate_invoice_review(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> FinanceAssociateReviewResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.get_review(
        current_user.id,
        invoice_id,
    )
