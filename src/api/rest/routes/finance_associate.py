from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.core.services.finance_associate_service import (
    FinanceAssociateService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardPaginationParams,
)
from src.schemas.finance_associate_schema import (
    FinanceAssociateSummaryResponse,
)
from src.schemas.invoice_review_schema import (
    InvoiceReviewResponse,
)

router = APIRouter(
    prefix="/finance-associate",
    tags=["Finance Associate"],
)

FINANCE_ASSOCIATE_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
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
    response_model=FinanceAssociateSummaryResponse,
)
async def get_finance_associate_dashboard_summary(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *FINANCE_ASSOCIATE_ROLES,
        ),
    ),
) -> FinanceAssociateSummaryResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.get_summary(
        current_user.id,
    )


@router.get(
    "/invoices/ready-for-approval",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_ready_for_approval_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
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
        pagination,
    )


@router.get(
    "/invoices/needs-review",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_needs_review_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
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
        pagination,
    )


@router.get(
    "/invoices/ready-to-pay",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_ready_to_pay_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
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
        pagination,
    )


@router.get(
    "/invoices/rejected",
    response_model=DashboardInvoiceListResponse,
)
async def list_finance_associate_rejected_invoices(
    pagination: DashboardPaginationParams = Depends(
        _pagination_params,
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
        pagination,
    )


@router.get(
    "/invoices/{invoice_id}/review",
    response_model=InvoiceReviewResponse,
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
) -> InvoiceReviewResponse:
    service = FinanceAssociateService(
        db,
    )

    return await service.get_review(
        current_user.id,
        invoice_id,
    )
