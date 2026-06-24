from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.api.rest.routes.invoice_roles import (
    INVOICE_REVIEW_ROLES,
)
from src.core.services.approve_invoice_service import (
    ApproveInvoiceService,
)
from src.data.models.postgres.users import User
from src.schemas.approval_schema import (
    ApproveInvoiceRequest,
    ApproveInvoiceResponse,
)

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)


@router.post(
    "/{invoice_id}/approve",
    response_model=ApproveInvoiceResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_invoice(
    invoice_id: UUID,
    request: ApproveInvoiceRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> ApproveInvoiceResponse:
    if request.approved_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="approved_by must match the authenticated user.",
        )

    service = ApproveInvoiceService(
        db,
    )

    return await service.approve_invoice(
        invoice_id,
        request,
    )
