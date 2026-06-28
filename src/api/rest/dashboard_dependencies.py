from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db_session
from src.core.services.overdue_refresh_service import (
    OverdueRefreshService,
)


async def ensure_overdue_refreshed(
    db: AsyncSession,
) -> None:
    service = OverdueRefreshService(
        db,
    )

    await service.refresh_if_required()


async def run_overdue_refresh_if_required(
    db: AsyncSession = Depends(
        get_db_session,
    ),
) -> None:
    await ensure_overdue_refreshed(
        db,
    )
