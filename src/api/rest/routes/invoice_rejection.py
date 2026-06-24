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
from src.core.services.reject_invoice_service import (
    RejectInvoiceService,
)
from src.core.services.rejection_draft_service import (
    RejectionDraftService,
)
from src.core.services.rejection_email_service import (
    RejectionEmailService,
)
from src.data.models.postgres.users import User
from src.schemas.rejection_schema import (
    RejectInvoiceRequest,
    RejectInvoiceResponse,
    RejectionDraftResponse,
    SendRejectionEmailRequest,
    SendRejectionEmailResponse,
)

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)


@router.post(
    "/{invoice_id}/reject",
    response_model=RejectInvoiceResponse,
    status_code=status.HTTP_200_OK,
)
async def reject_invoice(
    invoice_id: UUID,
    request: RejectInvoiceRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> RejectInvoiceResponse:
    if request.rejected_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="rejected_by must match the authenticated user.",
        )

    service = RejectInvoiceService(
        db,
    )

    return await service.reject_invoice(
        invoice_id,
        request,
    )


@router.post(
    "/{invoice_id}/rejection-draft",
    response_model=RejectionDraftResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_rejection_draft(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> RejectionDraftResponse:
    service = RejectionDraftService(
        db,
    )

    return await service.generate_draft(
        invoice_id,
    )


@router.post(
    "/{invoice_id}/rejection-send",
    response_model=SendRejectionEmailResponse,
    status_code=status.HTTP_200_OK,
)
async def send_rejection_email(
    invoice_id: UUID,
    request: SendRejectionEmailRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> SendRejectionEmailResponse:
    if request.sent_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="sent_by must match the authenticated user.",
        )

    service = RejectionEmailService(
        db,
    )

    return await service.send_rejection_email(
        invoice_id,
        request,
    )
