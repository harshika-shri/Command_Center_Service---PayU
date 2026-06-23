from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
    ValidationEventProcessingError,
)
from src.core.services.invoice_workflow_service import (
    InvoiceWorkflowService,
    WorkflowProcessingResult,
)
from src.utils.redis_stream_message_utils import (
    is_validation_error,
    parse_validation_event,
)

logger = logging.getLogger(__name__)


class ValidationEventHandlerService:
    async def handle_message(
        self,
        *,
        session: AsyncSession,
        fields: dict[str, object],
    ) -> WorkflowProcessingResult:
        try:
            event = parse_validation_event(
                fields,
            )
        except Exception as error:
            if is_validation_error(
                error,
            ):
                raise ValidationEventProcessingError(
                    f"Invalid validation event payload: {error}",
                ) from error

            raise

        workflow_service = InvoiceWorkflowService(
            session,
        )

        try:
            return await workflow_service.process_validation_event(
                event,
            )
        except InvoiceNotFoundError:
            logger.error(
                "Invoice not found for validation event invoice_id=%s event_type=%s",
                event.invoice_id,
                event.event_type,
            )
            raise

    @staticmethod
    def should_acknowledge_without_retry(
        error: Exception,
    ) -> bool:
        return isinstance(
            error,
            (
                ValidationEventProcessingError,
                InvoiceNotFoundError,
            ),
        )
