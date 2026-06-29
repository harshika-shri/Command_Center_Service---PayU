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

    async def start(self) -> None:
        if self._running:
            return

        self._redis = get_redis_client()
        self._session_factory = get_session_factory()
        await self._ensure_consumer_group()
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
                "Created Redis consumer group=%s",
                settings.VALIDATION_EVENTS_CONSUMER_GROUP,
            )
        except ResponseError as error:
            if "BUSYGROUP" not in str(
                error,
            ):
                raise

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

        try:
            response = await self._redis.xreadgroup(
                groupname=settings.VALIDATION_EVENTS_CONSUMER_GROUP,
                consumername=settings.VALIDATION_EVENTS_CONSUMER_NAME,
                streams={
                    settings.VALIDATION_EVENTS_STREAM: ">",
                },
                count=settings.REDIS_STREAM_BATCH_SIZE,
                block=settings.REDIS_STREAM_BLOCK_MS,
            )
        except TimeoutError:
            return

        if not response:
            return

        for _stream_name, messages in response:
            for message_id, fields in messages:
                await self._process_message(
                    message_id=message_id,
                    fields=fields,
                )

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
                await self._redis.xack(
                    settings.VALIDATION_EVENTS_STREAM,
                    settings.VALIDATION_EVENTS_CONSUMER_GROUP,
                    message_id,
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
                    await self._redis.xack(
                        settings.VALIDATION_EVENTS_STREAM,
                        settings.VALIDATION_EVENTS_CONSUMER_GROUP,
                        message_id,
                    )
                    return

                if attempt > settings.REDIS_STREAM_MAX_RETRIES:
                    logger.exception(
                        "Validation event processing failed after retries "
                        "message_id=%s",
                        message_id,
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


_consumer: ValidationStreamConsumer | None = None


def get_validation_stream_consumer() -> ValidationStreamConsumer:
    global _consumer

    if _consumer is None:
        _consumer = ValidationStreamConsumer()

    return _consumer
