from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.core.services.take_ownership_service import (
    TakeOwnershipService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.ownership_schema import (
    TakeOwnershipRequest,
    TakeOwnershipResponse,
)

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)

TAKE_OWNERSHIP_ROLES = (
    UserRole.FINANCE_MANAGER,
)


@router.post(
    "/{invoice_id}/take-ownership",
    response_model=TakeOwnershipResponse,
    status_code=status.HTTP_200_OK,
)
async def take_invoice_ownership(
    invoice_id: UUID,
    request: TakeOwnershipRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *TAKE_OWNERSHIP_ROLES,
        ),
    ),
) -> TakeOwnershipResponse:
    if request.manager_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="manager_id must match the authenticated user.",
        )

    service = TakeOwnershipService(
        db,
    )

    return await service.take_ownership(
        invoice_id,
        request,
    )
