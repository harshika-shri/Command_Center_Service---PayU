from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.sse.sse_event_publisher import SSEEventPublisher
from src.data.models.postgres.enums import InvoiceStatus
from src.data.repositories.invoice_repo import InvoiceRepository

logger = logging.getLogger(__name__)


class WorkflowReconciliationService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._invoice_repo = InvoiceRepository(
            session,
        )
        self._audit_log_service = AuditLogService(
            session,
        )

    async def reconcile_validated_invoices_missing_review_status(
        self,
    ) -> int:
        stuck_invoices = (
            await self._invoice_repo.find_validated_invoices_missing_under_review()
        )

        if not stuck_invoices:
            return 0

        reconciled_count = 0

        for snapshot in stuck_invoices:
            if snapshot.validation_outcome is None:
                continue

            previous_status = self._audit_log_service.format_invoice_status(
                snapshot.invoice_status,
            )

            await self._invoice_repo.update_invoice_status(
                snapshot.invoice_id,
                invoice_status=InvoiceStatus.UNDER_REVIEW,
            )
            await self._audit_log_service.create_audit_log(
                AuditLogCreatePayload(
                    invoice_id=snapshot.invoice_id,
                    action="VALIDATION_WORKFLOW_RECONCILED",
                    old_status=previous_status,
                    new_status=InvoiceStatus.UNDER_REVIEW.value,
                    remarks=(
                        "Reconciled invoice workflow state after validation "
                        "completed without under_review status."
                    ),
                ),
            )

            try:
                await SSEEventPublisher.schedule_invoice_state_change(
                    self._invoice_repo.session,
                    invoice_id=snapshot.invoice_id,
                    invoice_status=InvoiceStatus.UNDER_REVIEW,
                    validation_outcome=snapshot.validation_outcome,
                )
            except Exception:
                logger.exception(
                    "Failed to schedule SSE for reconciled invoice "
                    "invoice_id=%s",
                    snapshot.invoice_id,
                )

            reconciled_count += 1
            logger.info(
                "Reconciled validated invoice workflow state "
                "invoice_id=%s validation_outcome=%s old_status=%s "
                "new_status=%s",
                snapshot.invoice_id,
                snapshot.validation_outcome.value,
                previous_status,
                InvoiceStatus.UNDER_REVIEW.value,
            )

        return reconciled_count
