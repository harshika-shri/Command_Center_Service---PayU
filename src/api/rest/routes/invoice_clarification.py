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
from src.core.services.clarification_draft_service import (
    ClarificationDraftService,
)
from src.core.services.clarification_email_service import (
    ClarificationEmailService,
)
from src.data.models.postgres.users import User
from src.schemas.clarification_schema import (
    ClarificationDraftResponse,
    SendClarificationRequest,
    SendClarificationResponse,
)

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)


@router.post(
    "/{invoice_id}/clarification-draft",
    response_model=ClarificationDraftResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_clarification_draft(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> ClarificationDraftResponse:
    service = ClarificationDraftService(
        db,
    )

    return await service.generate_draft(
        invoice_id,
    )


@router.post(
    "/{invoice_id}/clarification-send",
    response_model=SendClarificationResponse,
    status_code=status.HTTP_200_OK,
)
async def send_clarification_email(
    invoice_id: UUID,
    request: SendClarificationRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> SendClarificationResponse:
    if request.sent_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="sent_by must match the authenticated user.",
        )

    service = ClarificationEmailService(
        db,
    )

    return await service.send_clarification(
        invoice_id,
        request,
    )
