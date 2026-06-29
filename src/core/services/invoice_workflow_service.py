from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
    ValidationEventProcessingError,
)
from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.services.notification_service import (
    NotificationService,
)
from src.core.sse.sse_event_publisher import SSEEventPublisher
from src.core.workflow.validation_workflow_mapping import (
    WORKFLOW_TRANSITIONS,
    WorkflowTransition,
)
from src.data.repositories.invoice_repo import (
    InvoiceRepository,
    InvoiceWorkflowSnapshot,
)
from src.schemas.validation_event_schema import (
    ValidationCompletedEvent,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkflowProcessingResult:
    invoice_id: UUID
    processed: bool
    duplicate: bool
    target_status: str | None = None


class InvoiceWorkflowService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.invoice_repo = InvoiceRepository(
            session,
        )
        self.audit_log_service = AuditLogService(
            session,
        )
        self.notification_service = NotificationService(
            session,
        )

    async def process_validation_event(
        self,
        event: ValidationCompletedEvent,
    ) -> WorkflowProcessingResult:
        transition = WORKFLOW_TRANSITIONS[event.validation_outcome]
        snapshot = await self.invoice_repo.get_workflow_snapshot(
            event.invoice_id,
        )

        if snapshot is None:
            raise InvoiceNotFoundError(
                str(event.invoice_id),
            )

        expected_outcome = transition.target_validation_outcome

        if snapshot.validation_outcome != expected_outcome:
            raise ValidationEventProcessingError(
                "Validation outcome on invoice does not match event payload.",
            )

        if self._is_duplicate_event(
            snapshot,
            transition,
        ):
            logger.info(
                "Skipping duplicate validation event "
                "invoice_id=%s event_type=%s current_status=%s",
                event.invoice_id,
                event.event_type,
                snapshot.invoice_status.value
                if snapshot.invoice_status is not None
                else None,
            )

            return WorkflowProcessingResult(
                invoice_id=event.invoice_id,
                processed=False,
                duplicate=True,
                target_status=transition.target_status.value,
            )

        previous_status = self.audit_log_service.format_invoice_status(
            snapshot.invoice_status,
        )

        await self.invoice_repo.update_invoice_status(
            event.invoice_id,
            invoice_status=transition.target_status,
        )
        await self.audit_log_service.create_audit_log(
            AuditLogCreatePayload(
                invoice_id=event.invoice_id,
                action=transition.audit_action,
                old_status=previous_status,
                new_status=transition.target_status.value,
                remarks=transition.remarks,
            ),
        )

        logger.info(
            "Invoice workflow updated invoice_id=%s "
            "event_type=%s old_status=%s new_status=%s",
            event.invoice_id,
            event.event_type,
            previous_status,
            transition.target_status.value,
        )

        await self.notification_service.notify_invoice_assigned(
            event.invoice_id,
        )

        await SSEEventPublisher.schedule_invoice_state_change(
            self.invoice_repo.session,
            invoice_id=event.invoice_id,
            invoice_status=transition.target_status,
            validation_outcome=transition.target_validation_outcome,
        )

        return WorkflowProcessingResult(
            invoice_id=event.invoice_id,
            processed=True,
            duplicate=False,
            target_status=transition.target_status.value,
        )

    @staticmethod
    def _is_duplicate_event(
        snapshot: InvoiceWorkflowSnapshot,
        transition: WorkflowTransition,
    ) -> bool:
        return (
            snapshot.invoice_status == transition.target_status
            and snapshot.validation_outcome
            == transition.target_validation_outcome
        )
