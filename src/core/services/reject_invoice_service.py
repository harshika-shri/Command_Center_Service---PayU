from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.rejection_exc import (
    InvoiceRejectionConflictError,
    InvoiceRejectionValidationError,
)
from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.services.invoice_ownership_service import (
    InvoiceOwnershipService,
)
from src.core.workflow.invoice_workflow_buckets import (
    is_eligible_for_business_rejection,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
)
from src.data.repositories.rejection_repo import (
    RejectionRepository,
)
from src.data.repositories.user_repo import (
    UserRepository,
)
from src.schemas.rejection_schema import (
    RejectInvoiceRequest,
    RejectInvoiceResponse,
)


class RejectInvoiceService:
    SUCCESS_MESSAGE = "Invoice rejected successfully."

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.rejection_repo = RejectionRepository(
            session,
        )
        self.user_repo = UserRepository(
            session,
        )
        self.audit_log_service = AuditLogService(
            session,
        )
        self.ownership_service = InvoiceOwnershipService(
            session,
        )

    async def reject_invoice(
        self,
        invoice_id: UUID,
        request: RejectInvoiceRequest,
    ) -> RejectInvoiceResponse:
        snapshot = await self.rejection_repo.get_invoice_for_update(
            invoice_id,
        )

        if snapshot is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        previous_status = self._validate_invoice_eligibility(
            snapshot.invoice_status,
        )

        rejecting_user = await self.user_repo.get_user_by_id(
            request.rejected_by,
        )

        if rejecting_user is None or not rejecting_user.is_active:
            raise InvoiceRejectionValidationError(
                "Rejecting user must be an active user.",
            )

        await self.ownership_service.ensure_can_take_action(
            user_id=request.rejected_by,
            user_role=rejecting_user.role,
            invoice_id=invoice_id,
        )

        rejection_reason = request.rejection_reason.strip()

        if not rejection_reason:
            raise InvoiceRejectionValidationError(
                "rejection_reason must contain meaningful content.",
            )

        await self.rejection_repo.reject_invoice(
            invoice_id,
            rejection_reason,
        )

        await self.audit_log_service.create_audit_log(
            AuditLogCreatePayload(
                invoice_id=invoice_id,
                action="REJECT_INVOICE",
                old_status=previous_status,
                new_status=InvoiceStatus.REJECTED.value,
                remarks=rejection_reason,
                performed_by=request.rejected_by,
            ),
        )

        return RejectInvoiceResponse(
            invoice_id=invoice_id,
            invoice_status=InvoiceStatus.REJECTED.value,
            message=self.SUCCESS_MESSAGE,
        )

    @staticmethod
    def _validate_invoice_eligibility(
        invoice_status: InvoiceStatus | None,
    ) -> str:
        if invoice_status == InvoiceStatus.REJECTED:
            raise InvoiceRejectionConflictError(
                "Invoice has already been rejected.",
            )

        if invoice_status == InvoiceStatus.READY_TO_PAY:
            raise InvoiceRejectionConflictError(
                "Invoice approved for payment cannot be rejected.",
            )

        if not is_eligible_for_business_rejection(
            invoice_status,
        ):
            raise InvoiceRejectionConflictError(
                "Invoice is not in an eligible state for rejection.",
            )

        return invoice_status.value
