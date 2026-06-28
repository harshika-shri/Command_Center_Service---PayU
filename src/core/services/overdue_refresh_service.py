from __future__ import annotations

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.services.notification_service import (
    NotificationService,
)
from src.core.sse.sse_event_publisher import SSEEventPublisher
from src.data.models.postgres.enums import (
    InvoiceStatus,
)
from src.data.repositories.overdue_invoice_repository import (
    OverdueCandidateRow,
    OverdueInvoiceRepository,
)
from src.data.repositories.system_jobs_repository import (
    OVERDUE_REFRESH_JOB_NAME,
    SystemJobsRepository,
)

logger = logging.getLogger(
    __name__,
)

_OVERDUE_AUDIT_ACTION = "MARK_OVERDUE"
_OVERDUE_AUDIT_REMARKS = "Invoice automatically marked as overdue."


class OverdueRefreshService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.system_jobs_repo = SystemJobsRepository(
            session,
        )
        self.overdue_invoice_repo = OverdueInvoiceRepository(
            session,
        )
        self.audit_log_service = AuditLogService(
            session,
        )
        self.notification_service = NotificationService(
            session,
        )

    async def refresh_if_required(
        self,
    ) -> None:
        today = date.today()
        await self._refresh_for_today(
            today,
        )

    async def _refresh_for_today(
        self,
        today: date,
    ) -> None:
        job = await self.system_jobs_repo.get_job_for_update(
            OVERDUE_REFRESH_JOB_NAME,
        )

        if job is None:
            logger.warning(
                "System job row missing for %s",
                OVERDUE_REFRESH_JOB_NAME,
            )
            return

        candidates = (
            await self.overdue_invoice_repo.fetch_invoices_to_mark_overdue(
                today,
            )
        )

        if candidates:
            await self.overdue_invoice_repo.mark_invoices_overdue(
                [candidate.invoice_id for candidate in candidates],
            )

            for candidate in candidates:
                await self._record_overdue_side_effects(
                    candidate,
                )

        await self.system_jobs_repo.update_last_run_date(
            OVERDUE_REFRESH_JOB_NAME,
            today,
        )

    async def _record_overdue_side_effects(
        self,
        candidate: OverdueCandidateRow,
    ) -> None:
        await self.audit_log_service.create_audit_log(
            AuditLogCreatePayload(
                invoice_id=candidate.invoice_id,
                action=_OVERDUE_AUDIT_ACTION,
                old_status=candidate.previous_status,
                new_status=InvoiceStatus.OVERDUE.value,
                remarks=_OVERDUE_AUDIT_REMARKS,
                performed_by=None,
            ),
        )

        await self.notification_service.notify_invoice_overdue(
            invoice_id=candidate.invoice_id,
            invoice_number=candidate.invoice_number,
            vendor_name=candidate.vendor_name,
            due_date=candidate.due_date,
        )

        validation_outcome = candidate.validation_outcome

        if validation_outcome is None:
            return

        await SSEEventPublisher.schedule_invoice_state_change(
            self.session,
            invoice_id=candidate.invoice_id,
            invoice_status=InvoiceStatus.OVERDUE,
            validation_outcome=validation_outcome,
        )
