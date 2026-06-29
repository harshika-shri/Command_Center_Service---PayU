from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sse_starlette import EventSourceResponse

from src.api.rest.dependencies import (
    get_access_token_payload,
)
from src.core.security.role_utils import parse_user_role
from src.core.sse.sse_event_publisher import (
    SSEEventPublisher,
)
from src.core.sse.sse_manager import (
    HEARTBEAT_INTERVAL_SECONDS,
    get_sse_manager,
)
from src.data.clients.postgres_client import get_session_factory
from src.data.repositories.user_repo import UserRepository

logger = logging.getLogger(
    __name__,
)

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


async def get_current_user_id_for_sse(
    payload: dict[str, object] = Depends(
        get_access_token_payload,
    ),
) -> UUID:
    session_factory = get_session_factory()

    async with session_factory() as session:
        repo = UserRepository(
            session,
        )
        user = await repo.get_user_by_id(
            UUID(
                str(
                    payload["sub"],
                ),
            ),
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )

        token_role = parse_user_role(
            payload.get(
                "role",
            ),
        )

        if user.role.value != token_role.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token role does not match user record",
            )

        return user.id


@router.get(
    "/stream",
)
async def events_stream(
    request: Request,
    user_id: UUID = Depends(
        get_current_user_id_for_sse,
    ),
) -> EventSourceResponse:
    sse_manager = get_sse_manager()

    async def event_generator():
        connection_id, queue = await sse_manager.connect(
            user_id,
        )

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    message = await asyncio.wait_for(
                        queue.get(),
                        timeout=HEARTBEAT_INTERVAL_SECONDS,
                    )
                except asyncio.TimeoutError:
                    yield {
                        "event": "heartbeat",
                        "data": SSEEventPublisher.serialize_payload(
                            {
                                "timestamp": datetime.now(
                                    UTC,
                                ).isoformat(),
                            },
                        ),
                    }
                    continue
                except Exception:
                    logger.exception(
                        "SSE stream error user_id=%s",
                        user_id,
                    )
                    break

                payload = message.get(
                    "data",
                )

                if not isinstance(
                    payload,
                    dict,
                ):
                    continue

                yield {
                    "event": str(
                        message.get(
                            "event",
                            "message",
                        ),
                    ),
                    "data": SSEEventPublisher.serialize_payload(
                        payload,
                    ),
                }
        finally:
            await sse_manager.disconnect(
                connection_id,
            )

    return EventSourceResponse(
        event_generator(),
    )
