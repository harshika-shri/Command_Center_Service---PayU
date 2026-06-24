from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.api.rest.routes.invoice_roles import (
    ESCALATION_ROLES,
)
from src.core.services.escalate_invoice_service import (
    EscalateInvoiceService,
)
from src.data.models.postgres.users import User
from src.schemas.escalation_schema import (
    EscalateInvoiceRequest,
    EscalateInvoiceResponse,
)

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)


@router.post(
    "/{invoice_id}/escalate",
    response_model=EscalateInvoiceResponse,
    status_code=status.HTTP_200_OK,
)
async def escalate_invoice(
    invoice_id: UUID,
    request: EscalateInvoiceRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *ESCALATION_ROLES,
        ),
    ),
) -> EscalateInvoiceResponse:
    if request.escalated_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="escalated_by must match the authenticated user.",
        )

    service = EscalateInvoiceService(
        db,
    )

    return await service.escalate_invoice(
        invoice_id,
        request,
    )
