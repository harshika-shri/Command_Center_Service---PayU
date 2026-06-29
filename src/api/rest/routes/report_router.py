from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.constants.report_constants import (
    ReportAssociateViewMode,
    ReportInvoiceStatus,
    ReportIssueSeverity,
    ReportOverdueFilter,
    ReportValidationNode,
    ReportValidationOutcome,
)
from src.core.services.report_service import ReportService
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.report_schema import (
    FinanceAssociatePerformanceListResponse,
    FinanceAssociateReportQueryParams,
    InvoiceReportListResponse,
    InvoiceReportQueryParams,
    ReportFilterOptionsResponse,
)

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)

REPORT_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
    UserRole.FINANCE_MANAGER,
)


def _invoice_report_params(
    from_date: date | None = Query(
        default=None,
    ),
    to_date: date | None = Query(
        default=None,
    ),
    invoice_status: ReportInvoiceStatus | None = Query(
        default=None,
    ),
    validation_outcome: ReportValidationOutcome | None = Query(
        default=None,
    ),
    vendor_id: UUID | None = Query(
        default=None,
    ),
    finance_associate_id: UUID | None = Query(
        default=None,
    ),
    validation_node: ReportValidationNode | None = Query(
        default=None,
    ),
    issue_severity: ReportIssueSeverity | None = Query(
        default=None,
    ),
    overdue: ReportOverdueFilter = Query(
        default=ReportOverdueFilter.ALL,
    ),
    po_number: str | None = Query(
        default=None,
    ),
    invoice_number: str | None = Query(
        default=None,
    ),
    search: str | None = Query(
        default=None,
    ),
    sort_by: str = Query(
        default="invoice_date",
    ),
    sort_dir: str = Query(
        default="desc",
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> InvoiceReportQueryParams:
    return InvoiceReportQueryParams(
        from_date=from_date,
        to_date=to_date,
        invoice_status=invoice_status,
        validation_outcome=validation_outcome,
        vendor_id=vendor_id,
        finance_associate_id=finance_associate_id,
        validation_node=validation_node,
        issue_severity=issue_severity,
        overdue=overdue,
        po_number=po_number,
        invoice_number=invoice_number,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


def _associate_report_params(
    from_date: date | None = Query(
        default=None,
    ),
    to_date: date | None = Query(
        default=None,
    ),
    finance_associate_id: UUID | None = Query(
        default=None,
    ),
    view_mode: ReportAssociateViewMode = Query(
        default=ReportAssociateViewMode.OVERALL,
    ),
    search: str | None = Query(
        default=None,
    ),
    sort_by: str = Query(
        default="associate_name",
    ),
    sort_dir: str = Query(
        default="asc",
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> FinanceAssociateReportQueryParams:
    return FinanceAssociateReportQueryParams(
        from_date=from_date,
        to_date=to_date,
        finance_associate_id=finance_associate_id,
        view_mode=view_mode,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/filter-options",
    response_model=ReportFilterOptionsResponse,
)
async def get_report_filter_options(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *REPORT_ROLES,
        ),
    ),
) -> ReportFilterOptionsResponse:
    service = ReportService(
        db,
    )

    return await service.get_filter_options(
        current_user=current_user,
    )


@router.get(
    "/invoices",
    response_model=InvoiceReportListResponse,
)
async def list_invoice_processing_report(
    params: InvoiceReportQueryParams = Depends(
        _invoice_report_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *REPORT_ROLES,
        ),
    ),
) -> InvoiceReportListResponse:
    if current_user.role == UserRole.FINANCE_ASSOCIATE:
        params = params.model_copy(
            update={
                "finance_associate_id": None,
            },
        )

    service = ReportService(
        db,
    )

    return await service.list_invoice_report(
        params=params,
        current_user=current_user,
    )


@router.get(
    "/invoices/export",
)
async def export_invoice_processing_report(
    params: InvoiceReportQueryParams = Depends(
        _invoice_report_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *REPORT_ROLES,
        ),
    ),
):
    if current_user.role == UserRole.FINANCE_ASSOCIATE:
        params = params.model_copy(
            update={
                "finance_associate_id": None,
            },
        )

    service = ReportService(
        db,
    )

    return await service.export_invoice_report(
        params=params,
        current_user=current_user,
    )


@router.get(
    "/finance-associates",
    response_model=FinanceAssociatePerformanceListResponse,
)
async def list_finance_associate_performance_report(
    params: FinanceAssociateReportQueryParams = Depends(
        _associate_report_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *REPORT_ROLES,
        ),
    ),
) -> FinanceAssociatePerformanceListResponse:
    if current_user.role == UserRole.FINANCE_ASSOCIATE:
        params = params.model_copy(
            update={
                "finance_associate_id": None,
            },
        )

    service = ReportService(
        db,
    )

    return await service.list_associate_performance(
        params=params,
        current_user=current_user,
    )


@router.get(
    "/finance-associates/export",
)
async def export_finance_associate_performance_report(
    params: FinanceAssociateReportQueryParams = Depends(
        _associate_report_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *REPORT_ROLES,
        ),
    ),
):
    if current_user.role == UserRole.FINANCE_ASSOCIATE:
        params = params.model_copy(
            update={
                "finance_associate_id": None,
            },
        )

    service = ReportService(
        db,
    )

    return await service.export_associate_performance(
        params=params,
        current_user=current_user,
    )
