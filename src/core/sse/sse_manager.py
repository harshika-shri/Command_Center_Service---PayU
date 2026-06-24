from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

logger = logging.getLogger(
    __name__,
)

HEARTBEAT_INTERVAL_SECONDS = 30.0


@dataclass(slots=True)
class SSEClientConnection:
    user_id: UUID
    queue: asyncio.Queue[dict[str, object]]
    connected_at: datetime


class SSEManager:
    def __init__(
        self,
    ) -> None:
        self._connections: dict[str, SSEClientConnection] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task[None] | None = None

    async def start(
        self,
    ) -> None:
        if self._heartbeat_task is not None:
            return

        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
        )

    async def stop(
        self,
    ) -> None:
        if self._heartbeat_task is None:
            return

        self._heartbeat_task.cancel()

        try:
            await self._heartbeat_task
        except asyncio.CancelledError:
            pass

        self._heartbeat_task = None

    async def connect(
        self,
        user_id: UUID,
    ) -> tuple[str, asyncio.Queue[dict[str, object]]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        connection_id = str(
            uuid4(),
        )

        async with self._lock:
            self._connections[connection_id] = SSEClientConnection(
                user_id=user_id,
                queue=queue,
                connected_at=datetime.now(
                    UTC,
                ),
            )

        return connection_id, queue

    async def disconnect(
        self,
        connection_id: str,
    ) -> None:
        async with self._lock:
            self._connections.pop(
                connection_id,
                None,
            )

    async def send_to_user(
        self,
        user_id: UUID,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        message = {
            "event": event_type,
            "data": payload,
        }

        async with self._lock:
            targets = [
                connection
                for connection in self._connections.values()
                if connection.user_id == user_id
            ]

        for connection in targets:
            try:
                await connection.queue.put(
                    message,
                )
            except Exception:
                logger.exception(
                    "Failed to enqueue SSE event user_id=%s event_type=%s",
                    user_id,
                    event_type,
                )

    async def broadcast(
        self,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        message = {
            "event": event_type,
            "data": payload,
        }

        async with self._lock:
            targets = list(
                self._connections.values(),
            )

        for connection in targets:
            try:
                await connection.queue.put(
                    message,
                )
            except Exception:
                logger.exception(
                    "Failed to broadcast SSE event event_type=%s",
                    event_type,
                )

    async def _heartbeat_loop(
        self,
    ) -> None:
        while True:
            await asyncio.sleep(
                HEARTBEAT_INTERVAL_SECONDS,
            )

            payload = {
                "timestamp": datetime.now(
                    UTC,
                ).isoformat(),
            }

            try:
                await self.broadcast(
                    event_type="heartbeat",
                    payload=payload,
                )
            except Exception:
                logger.exception(
                    "Failed to send SSE heartbeat",
                )


_sse_manager: SSEManager | None = None


def get_sse_manager() -> SSEManager:
    global _sse_manager

    if _sse_manager is None:
        _sse_manager = SSEManager()

    return _sse_manager
