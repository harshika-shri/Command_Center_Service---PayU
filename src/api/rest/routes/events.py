from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


@router.get("/stream")
async def stream_events() -> EventSourceResponse:
    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        while True:
            yield {
                "event": "heartbeat",
                "data": "{}",
            }
            await asyncio.sleep(
                30,
            )

    return EventSourceResponse(
        event_generator(),
    )
