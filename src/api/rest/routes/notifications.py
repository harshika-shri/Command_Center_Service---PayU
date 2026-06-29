from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_current_user,
    get_db_session,
)
from src.api.rest.list_query_dependencies import (
    notification_list_query_params,
)
from src.core.services.notification_service import (
    NotificationService,
)
from src.data.models.postgres.users import User
from src.schemas.list_query_schema import NotificationListQueryParams
from src.schemas.notification_schema import (
    MarkAllNotificationsReadResponse,
    MarkNotificationReadResponse,
    NotificationListResponse,
    NotificationUnreadCountResponse,
)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=NotificationListResponse,
)
async def list_notifications(
    query: NotificationListQueryParams = Depends(
        notification_list_query_params,
    ),
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> NotificationListResponse:
    service = NotificationService(
        db,
    )

    return await service.list_notifications(
        current_user.id,
        query,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountResponse,
)
async def get_unread_notification_count(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> NotificationUnreadCountResponse:
    service = NotificationService(
        db,
    )

    return await service.get_unread_count(
        current_user.id,
    )


@router.post(
    "/read-all",
    response_model=MarkAllNotificationsReadResponse,
)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> MarkAllNotificationsReadResponse:
    service = NotificationService(
        db,
    )

    return await service.mark_all_read(
        current_user.id,
    )


@router.post(
    "/{notification_id}/read",
    response_model=MarkNotificationReadResponse,
)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
) -> MarkNotificationReadResponse:
    service = NotificationService(
        db,
    )

    return await service.mark_notification_read(
        user_id=current_user.id,
        notification_id=notification_id,
    )
