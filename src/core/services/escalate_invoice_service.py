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
from src.data.models.postgres.enums import (
    InvoiceStatus,
)
from src.data.repositories.escalation_repo import (
    EscalationRepository,
)
from src.schemas.escalation_schema import (
    EscalateInvoiceRequest,
    EscalateInvoiceResponse,
)

_ELIGIBLE_ESCALATION_STATUSES = frozenset(
    {
        InvoiceStatus.READY_FOR_APPROVAL,
        InvoiceStatus.PARTIALLY_APPROVED,
        InvoiceStatus.REJECTED,
    },
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

        manager = await self.escalation_repo.get_finance_manager(
            request.manager_id,
        )

        if manager is None:
            raise InvoiceEscalationValidationError(
                "Manager must be an active Finance Manager.",
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

        if (
            invoice_status is None
            or invoice_status not in _ELIGIBLE_ESCALATION_STATUSES
        ):
            raise InvoiceEscalationConflictError(
                "Invoice is not in an eligible state for escalation.",
            )

        return invoice_status.value
