from __future__ import annotations

import json
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.sse.sse_event_buffer import (
    PendingSSEEvent,
    append_pending_event,
    clear_pending_events,
    drain_pending_events,
)
from src.core.sse.sse_manager import (
    get_sse_manager,
)
from src.core.sse.sse_recipient_resolver import (
    SSERecipientResolver,
)
from src.core.workflow.invoice_workflow_buckets import (
    FinanceManagerBucket,
    resolve_dashboard_bucket,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)

logger = logging.getLogger(
    __name__,
)

OWNER_TYPE_FINANCE_MANAGER = "finance_manager"


class SSEEventPublisher:
    @staticmethod
    def schedule_notification_created(
        *,
        notification_id: UUID,
        user_id: UUID,
        title: str,
        message: str,
        invoice_id: UUID | None,
    ) -> None:
        payload: dict[str, object] = {
            "notification_id": str(
                notification_id,
            ),
            "title": title,
            "message": message,
            "invoice_id": (
                str(
                    invoice_id,
                )
                if invoice_id is not None
                else None
            ),
        }

        append_pending_event(
            PendingSSEEvent(
                event_type="notification_created",
                payload=payload,
                recipient_user_ids=frozenset(
                    {user_id},
                ),
            ),
        )

    @staticmethod
    def schedule_invoice_updated(
        *,
        invoice_id: UUID,
        invoice_status: str,
        validation_outcome: str,
        recipient_user_ids: frozenset[UUID],
    ) -> None:
        if not recipient_user_ids:
            return

        append_pending_event(
            PendingSSEEvent(
                event_type="invoice_updated",
                payload={
                    "invoice_id": str(
                        invoice_id,
                    ),
                    "invoice_status": invoice_status,
                    "validation_outcome": validation_outcome,
                },
                recipient_user_ids=recipient_user_ids,
            ),
        )

    @staticmethod
    def schedule_dashboard_updated(
        *,
        invoice_id: UUID,
        bucket: str,
        recipient_user_ids: frozenset[UUID],
    ) -> None:
        if not recipient_user_ids:
            return

        append_pending_event(
            PendingSSEEvent(
                event_type="dashboard_updated",
                payload={
                    "invoice_id": str(
                        invoice_id,
                    ),
                    "bucket": bucket,
                },
                recipient_user_ids=recipient_user_ids,
            ),
        )

    @staticmethod
    def schedule_ownership_changed(
        *,
        invoice_id: UUID,
        owner_type: str,
        owner_id: UUID,
        recipient_user_ids: frozenset[UUID],
    ) -> None:
        if not recipient_user_ids:
            return

        append_pending_event(
            PendingSSEEvent(
                event_type="ownership_changed",
                payload={
                    "invoice_id": str(
                        invoice_id,
                    ),
                    "owner_type": owner_type,
                    "owner_id": str(
                        owner_id,
                    ),
                },
                recipient_user_ids=recipient_user_ids,
            ),
        )

    @staticmethod
    async def schedule_invoice_state_change(
        session: AsyncSession,
        *,
        invoice_id: UUID,
        invoice_status: InvoiceStatus,
        validation_outcome: InvoiceValidationOutcome,
    ) -> None:
        resolver = SSERecipientResolver(
            session,
        )
        recipients = await resolver.resolve_invoice_recipients(
            invoice_id,
        )

        SSEEventPublisher.schedule_invoice_updated(
            invoice_id=invoice_id,
            invoice_status=invoice_status.value,
            validation_outcome=validation_outcome.value,
            recipient_user_ids=recipients,
        )

        bucket = resolve_dashboard_bucket(
            invoice_status=invoice_status,
            validation_outcome=validation_outcome,
        )

        if bucket is not None:
            SSEEventPublisher.schedule_dashboard_updated(
                invoice_id=invoice_id,
                bucket=bucket,
                recipient_user_ids=recipients,
            )

    @staticmethod
    async def schedule_escalation_events(
        session: AsyncSession,
        *,
        invoice_id: UUID,
        manager_id: UUID,
        associate_id: UUID | None,
        validation_outcome: InvoiceValidationOutcome,
    ) -> None:
        recipients: set[UUID] = {manager_id}

        if associate_id is not None:
            recipients.add(
                associate_id,
            )

        recipient_ids = frozenset(
            recipients,
        )

        SSEEventPublisher.schedule_invoice_updated(
            invoice_id=invoice_id,
            invoice_status=InvoiceStatus.ESCALATED.value,
            validation_outcome=validation_outcome.value,
            recipient_user_ids=recipient_ids,
        )
        SSEEventPublisher.schedule_ownership_changed(
            invoice_id=invoice_id,
            owner_type=OWNER_TYPE_FINANCE_MANAGER,
            owner_id=manager_id,
            recipient_user_ids=recipient_ids,
        )
        SSEEventPublisher.schedule_dashboard_updated(
            invoice_id=invoice_id,
            bucket=resolve_dashboard_bucket(
                invoice_status=InvoiceStatus.ESCALATED,
                validation_outcome=validation_outcome,
            )
            or InvoiceStatus.ESCALATED.value,
            recipient_user_ids=recipient_ids,
        )

    @staticmethod
    async def schedule_take_ownership_events(
        session: AsyncSession,
        *,
        invoice_id: UUID,
        manager_id: UUID,
        invoice_status: InvoiceStatus | None,
        validation_outcome: InvoiceValidationOutcome | None,
    ) -> None:
        recipients = frozenset(
            {manager_id},
        )

        SSEEventPublisher.schedule_ownership_changed(
            invoice_id=invoice_id,
            owner_type=OWNER_TYPE_FINANCE_MANAGER,
            owner_id=manager_id,
            recipient_user_ids=recipients,
        )

        if (
            invoice_status is not None
            and validation_outcome is not None
        ):
            SSEEventPublisher.schedule_invoice_updated(
                invoice_id=invoice_id,
                invoice_status=invoice_status.value,
                validation_outcome=validation_outcome.value,
                recipient_user_ids=recipients,
            )

            if invoice_status == InvoiceStatus.UNDER_REVIEW:
                bucket = (
                    FinanceManagerBucket.MY_CLAIMED_UNRESOLVED.value
                )
            else:
                bucket = resolve_dashboard_bucket(
                    invoice_status=invoice_status,
                    validation_outcome=validation_outcome,
                )

            if bucket is not None:
                SSEEventPublisher.schedule_dashboard_updated(
                    invoice_id=invoice_id,
                    bucket=bucket,
                    recipient_user_ids=recipients,
                )

    @staticmethod
    async def flush() -> None:
        pending_events = drain_pending_events()

        if not pending_events:
            return

        manager = get_sse_manager()

        for event in pending_events:
            for user_id in event.recipient_user_ids:
                try:
                    await manager.send_to_user(
                        user_id=user_id,
                        event_type=event.event_type,
                        payload=event.payload,
                    )
                except Exception:
                    logger.exception(
                        "Failed to publish SSE event "
                        "event_type=%s user_id=%s",
                        event.event_type,
                        user_id,
                    )

    @staticmethod
    def clear_pending() -> None:
        clear_pending_events()

    @staticmethod
    def serialize_payload(
        payload: dict[str, object],
    ) -> str:
        return json.dumps(
            payload,
        )
