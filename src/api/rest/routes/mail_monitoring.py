from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.core.services.mail_monitoring_service import (
    MailMonitoringService,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.mail_monitoring_schema import (
    RecentMailListResponse,
)

router = APIRouter(
    prefix="/mail-monitoring",
    tags=["Mail Monitoring"],
)

MAIL_MONITORING_ROLES = (
    UserRole.FINANCE_MANAGER,
)


@router.get(
    "/recent-mails",
    response_model=RecentMailListResponse,
)
async def list_recent_mail(
    mailbox: str | None = Query(
        default=None,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *MAIL_MONITORING_ROLES,
        ),
    ),
) -> RecentMailListResponse:
    service = MailMonitoringService(
        db,
    )

    return await service.list_recent_mail(
        mailbox=mailbox,
        limit=limit,
        offset=offset,
    )
