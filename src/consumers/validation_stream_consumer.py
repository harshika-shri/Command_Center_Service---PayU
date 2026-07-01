from __future__ import annotations

import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import ResponseError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config.settings import settings
from src.core.services.validation_event_handler_service import (
    ValidationEventHandlerService,
)
from src.core.sse.sse_event_publisher import SSEEventPublisher
from src.data.clients.postgres_client import (
    get_session_factory,
)
from src.data.clients.redis_client import (
    close_redis_client,
    get_redis_client,
)

logger = logging.getLogger(__name__)


class ValidationStreamConsumer:
    def __init__(self) -> None:
        self._redis: Redis | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._handler = ValidationEventHandlerService()
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._startup_recovery_pending = True

    async def start(self) -> None:
        if self._running:
            return

        self._redis = get_redis_client()
        self._session_factory = get_session_factory()
        await self._ensure_consumer_group()
        await self._recover_undelivered_stream_entries()
        self._running = True
        self._task = asyncio.create_task(
            self._consume_loop(),
        )
        logger.info(
            "Validation stream consumer started stream=%s group=%s consumer=%s",
            settings.VALIDATION_EVENTS_STREAM,
            settings.VALIDATION_EVENTS_CONSUMER_GROUP,
            settings.VALIDATION_EVENTS_CONSUMER_NAME,
        )

    async def stop(self) -> None:
        self._running = False

        if self._task is not None:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

        await close_redis_client()
        self._redis = None
        logger.info("Validation stream consumer stopped")

    async def _ensure_consumer_group(self) -> None:
        if self._redis is None:
            raise RuntimeError(
                "Redis client is not initialized.",
            )

        try:
            await self._redis.xgroup_create(
                name=settings.VALIDATION_EVENTS_STREAM,
                groupname=settings.VALIDATION_EVENTS_CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )
            logger.info(
                "Created Redis consumer group=%s stream=%s",
                settings.VALIDATION_EVENTS_CONSUMER_GROUP,
                settings.VALIDATION_EVENTS_STREAM,
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(
                error,
            ):
                raise

    async def _recover_undelivered_stream_entries(self) -> None:
        if self._redis is None:
            return

        try:
            stream_info = await self._redis.xinfo_stream(
                settings.VALIDATION_EVENTS_STREAM,
            )
            groups = await self._redis.xinfo_groups(
                settings.VALIDATION_EVENTS_STREAM,
            )
        except ResponseError:
            return

        group_info = next(
            (
                group
                for group in groups
                if group.get("name")
                == settings.VALIDATION_EVENTS_CONSUMER_GROUP
            ),
            None,
        )

        if group_info is None:
            return

        entries_read = int(
            group_info.get(
                "entries-read",
                0,
            )
            or 0,
        )
        stream_length = int(
            stream_info.get(
                "length",
                0,
            )
            or 0,
        )

        if entries_read >= stream_length:
            return

        reset_id = "0-0"

        logger.warning(
            "Recovering undelivered validation events "
            "entries_read=%s stream_length=%s reset_id=%s",
            entries_read,
            stream_length,
            reset_id,
        )

        await self._redis.xgroup_setid(
            settings.VALIDATION_EVENTS_STREAM,
            settings.VALIDATION_EVENTS_CONSUMER_GROUP,
            reset_id,
        )

        logger.info(
            "Validation consumer group read position synced for catch-up "
            "stream=%s group=%s",
            settings.VALIDATION_EVENTS_STREAM,
            settings.VALIDATION_EVENTS_CONSUMER_GROUP,
        )

    async def _consume_loop(self) -> None:
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error in validation stream consumer loop",
                )
                await asyncio.sleep(
                    1,
                )

    async def _poll_once(self) -> None:
        if self._redis is None or self._session_factory is None:
            return

        while True:
            processed_pending = await self._read_and_process_messages(
                stream_id="0",
                block_ms=None,
                recovery=self._startup_recovery_pending,
            )

            if not processed_pending:
                self._startup_recovery_pending = False
                break

        await self._read_and_process_messages(
            stream_id=">",
            block_ms=settings.REDIS_STREAM_BLOCK_MS,
            recovery=False,
        )

    async def _read_and_process_messages(
        self,
        *,
        stream_id: str,
        block_ms: int | None,
        recovery: bool,
    ) -> bool:
        if self._redis is None:
            return False

        try:
            read_kwargs: dict[str, object] = {
                "groupname": settings.VALIDATION_EVENTS_CONSUMER_GROUP,
                "consumername": settings.VALIDATION_EVENTS_CONSUMER_NAME,
                "streams": {
                    settings.VALIDATION_EVENTS_STREAM: stream_id,
                },
                "count": settings.REDIS_STREAM_BATCH_SIZE,
            }

            if block_ms is not None:
                read_kwargs["block"] = block_ms

            response = await self._redis.xreadgroup(
                **read_kwargs,
            )
        except TimeoutError:
            return False

        if not response:
            return False

        entry_count = sum(
            len(messages) for _, messages in response
        )

        if entry_count == 0:
            return False

        for _stream_name, messages in response:
            for message_id, fields in messages:
                if recovery:
                    logger.info(
                        "Pending validation message recovered after restart "
                        "message_id=%s",
                        message_id,
                    )

                await self._process_message(
                    message_id=message_id,
                    fields=fields,
                )

        return True

    async def _process_message(
        self,
        *,
        message_id: str,
        fields: dict[str, object],
    ) -> None:
        if self._redis is None or self._session_factory is None:
            return

        attempt = 0

        while attempt <= settings.REDIS_STREAM_MAX_RETRIES:
            attempt += 1

            try:
                async with self._session_factory() as session:
                    result = await self._handler.handle_message(
                        session=session,
                        fields=fields,
                    )
                    await session.commit()
                    await SSEEventPublisher.flush()

                logger.info(
                    "Processed validation stream message "
                    "message_id=%s invoice_id=%s processed=%s duplicate=%s",
                    message_id,
                    result.invoice_id,
                    result.processed,
                    result.duplicate,
                )
                await self._acknowledge_message(
                    message_id=message_id,
                    invoice_id=str(
                        result.invoice_id,
                    ),
                )
                return
            except Exception as error:
                SSEEventPublisher.clear_pending()

                if self._handler.should_acknowledge_without_retry(
                    error,
                ):
                    logger.error(
                        "Acknowledging non-retryable validation event "
                        "message_id=%s error=%s",
                        message_id,
                        error,
                    )
                    await self._acknowledge_message(
                        message_id=message_id,
                    )
                    return

                if attempt > settings.REDIS_STREAM_MAX_RETRIES:
                    logger.exception(
                        "Validation event processing failed after retries "
                        "message_id=%s",
                        message_id,
                    )
                    await self._acknowledge_message(
                        message_id=message_id,
                    )
                    return

                logger.warning(
                    "Retrying validation event processing message_id=%s attempt=%s",
                    message_id,
                    attempt,
                )
                await asyncio.sleep(
                    attempt,
                )

    async def _acknowledge_message(
        self,
        *,
        message_id: str,
        invoice_id: str | None = None,
    ) -> None:
        if self._redis is None:
            return

        await self._redis.xack(
            settings.VALIDATION_EVENTS_STREAM,
            settings.VALIDATION_EVENTS_CONSUMER_GROUP,
            message_id,
        )

        logger.info(
            "Redis message acknowledged stream=%s message_id=%s invoice_id=%s",
            settings.VALIDATION_EVENTS_STREAM,
            message_id,
            invoice_id,
        )


_consumer: ValidationStreamConsumer | None = None


def get_validation_stream_consumer() -> ValidationStreamConsumer:
    global _consumer

    if _consumer is None:
        _consumer = ValidationStreamConsumer()

    return _consumer
