from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.escalation_exc import (
    InvoiceEscalationConflictError,
    InvoiceEscalationValidationError,
)
from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.services.authorization_service import (
    AuthorizationService,
)
from src.core.services.invoice_ownership_service import (
    InvoiceOwnershipService,
)
from src.core.services.notification_service import (
    NotificationService,
)
from src.core.sse.sse_event_publisher import SSEEventPublisher
from src.core.workflow.invoice_workflow_buckets import (
    is_eligible_for_escalation,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.repositories.escalation_repo import (
    EscalationRepository,
)
from src.data.repositories.user_repo import (
    UserRepository,
)
from src.schemas.escalation_schema import (
    EscalateInvoiceRequest,
    EscalateInvoiceResponse,
)


class EscalateInvoiceService:
    SUCCESS_MESSAGE = "Invoice successfully escalated."

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.escalation_repo = EscalationRepository(
            session,
        )
        self.audit_log_service = AuditLogService(
            session,
        )
        self.ownership_service = InvoiceOwnershipService(
            session,
        )
        self.authorization_service = AuthorizationService(
            session,
        )
        self.user_repo = UserRepository(
            session,
        )
        self.notification_service = NotificationService(
            session,
        )

    async def escalate_invoice(
        self,
        invoice_id: UUID,
        request: EscalateInvoiceRequest,
    ) -> EscalateInvoiceResponse:
        snapshot = await self.escalation_repo.get_invoice_for_update(
            invoice_id,
        )

        if snapshot is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        previous_status = self._validate_invoice_eligibility(
            snapshot.invoice_status,
        )

        escalating_user = await self.user_repo.get_user_by_id(
            request.escalated_by,
        )

        if escalating_user is None:
            raise InvoiceEscalationValidationError(
                "Escalating user must be an active user.",
            )

        await self.authorization_service.ensure_can_escalate(
            user_id=request.escalated_by,
            user_role=escalating_user.role,
            invoice_id=invoice_id,
        )

        manager = await self.escalation_repo.get_finance_manager(
            request.manager_id,
        )

        if manager is None:
            raise InvoiceEscalationValidationError(
                "Manager must be an active Finance Manager.",
            )

        associate_id = await self.ownership_service.get_associate_owner_id(
            invoice_id,
        )

        await self.escalation_repo.escalate_invoice(
            invoice_id,
            request.manager_id,
        )

        await self.audit_log_service.create_audit_log(
            AuditLogCreatePayload(
                invoice_id=invoice_id,
                action="ESCALATE",
                old_status=previous_status,
                new_status=InvoiceStatus.ESCALATED.value,
                remarks=request.reason,
                performed_by=request.escalated_by,
            ),
        )

        await self.notification_service.notify_invoice_escalated(
            invoice_id=invoice_id,
            manager_id=request.manager_id,
            associate_id=associate_id,
        )

        await SSEEventPublisher.schedule_escalation_events(
            self.escalation_repo.session,
            invoice_id=invoice_id,
            manager_id=request.manager_id,
            associate_id=associate_id,
            validation_outcome=snapshot.validation_outcome
            or InvoiceValidationOutcome.RESOLVED,
        )

        return EscalateInvoiceResponse(
            invoice_id=invoice_id,
            invoice_status=InvoiceStatus.ESCALATED.value,
            escalated_to=request.manager_id,
            message=self.SUCCESS_MESSAGE,
        )

    @staticmethod
    def _validate_invoice_eligibility(
        invoice_status: InvoiceStatus | None,
    ) -> str:
        if invoice_status == InvoiceStatus.ESCALATED:
            raise InvoiceEscalationConflictError(
                "Invoice has already been escalated.",
            )

        if invoice_status == InvoiceStatus.READY_TO_PAY:
            raise InvoiceEscalationConflictError(
                "Invoice approved for payment cannot be escalated.",
            )

        if not is_eligible_for_escalation(
            invoice_status,
        ):
            raise InvoiceEscalationConflictError(
                "Invoice must be under human review to escalate.",
            )

        return invoice_status.value
