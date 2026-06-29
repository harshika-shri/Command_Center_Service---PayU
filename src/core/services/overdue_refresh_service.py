from __future__ import annotations

import logging
from datetime import date, datetime, timezone

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
from src.data.models.postgres.system_jobs import SystemJob
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


class OverdueRefreshConfigurationError(RuntimeError):
    """Raised when required system_jobs configuration is missing."""


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
        today = datetime.now(
            timezone.utc,
        ).date()
        job = await self.system_jobs_repo.get_job_for_update(
            OVERDUE_REFRESH_JOB_NAME,
        )

        if job is None:
            raise OverdueRefreshConfigurationError(
                "Required system_jobs row "
                f"'{OVERDUE_REFRESH_JOB_NAME}' is missing. "
                "This row is seeded by migration "
                "t1u5v4w39r08_create_system_jobs_table. "
                "Run `alembic upgrade head` in auth_service.",
            )

        if (
            job.last_run_date is not None
            and job.last_run_date >= today
        ):
            return

        await self._refresh_for_today(
            today,
            job,
        )

    async def _refresh_for_today(
        self,
        today: date,
        job: SystemJob,
    ) -> None:
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
            job,
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
