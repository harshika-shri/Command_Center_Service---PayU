from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.clarification_exc import (
    ClarificationConflictError,
    ClarificationValidationError,
)
from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.services.dispute_communication_service import (
    DisputeCommunicationService,
)
from src.core.services.dispute_service import (
    DisputeService,
)
from src.core.services.invoice_ownership_service import (
    InvoiceOwnershipService,
)
from src.core.services.sendgrid_service import (
    SendGridService,
)
from src.core.workflow.clarification_draft_builder import (
    ClarificationDraftBuilder,
)
from src.core.workflow.invoice_workflow_buckets import (
    is_eligible_for_clarification,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.repositories.clarification_repo import (
    ClarificationRepository,
)
from src.data.repositories.user_repo import (
    UserRepository,
)
from src.schemas.clarification_schema import (
    SendClarificationRequest,
    SendClarificationResponse,
)


class ClarificationEmailService:
    SUCCESS_MESSAGE = "Clarification email sent to vendor."
    AUDIT_REMARKS = "Clarification email sent to vendor."

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.clarification_repo = ClarificationRepository(
            session,
        )
        self.dispute_service = DisputeService(
            session,
        )
        self.dispute_communication_service = (
            DisputeCommunicationService(
                session,
            )
        )
        self.audit_log_service = AuditLogService(
            session,
        )
        self.sendgrid_service = SendGridService()
        self.draft_builder = ClarificationDraftBuilder()
        self.ownership_service = InvoiceOwnershipService(
            session,
        )
        self.user_repo = UserRepository(
            session,
        )

    async def send_clarification(
        self,
        invoice_id: UUID,
        request: SendClarificationRequest,
    ) -> SendClarificationResponse:
        snapshot = await self.clarification_repo.get_invoice_snapshot(
            invoice_id,
        )

        if snapshot is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        current_status = self._validate_invoice_eligibility(
            invoice_status=snapshot.invoice_status,
            validation_outcome=snapshot.validation_outcome,
        )

        sending_user = await self.user_repo.get_user_by_id(
            request.sent_by,
        )

        if sending_user is None:
            raise ClarificationValidationError(
                "Sending user must be an active user.",
            )

        await self.ownership_service.ensure_can_take_action(
            user_id=request.sent_by,
            user_role=sending_user.role,
            invoice_id=invoice_id,
        )

        vendor_email = await self.clarification_repo.get_vendor_email(
            invoice_id,
        )

        if not vendor_email:
            raise ClarificationValidationError(
                "Vendor email unavailable.",
            )

        html_content = self.draft_builder.plain_text_to_html(
            request.body,
        )

        self.sendgrid_service.send_email(
            to_email=vendor_email,
            subject=request.subject,
            html_content=html_content,
        )

        dispute = await self.dispute_service.create_clarification_dispute(
            invoice_id=invoice_id,
            raised_by=request.sent_by,
            summary=request.subject,
        )

        communication = (
            await self.dispute_communication_service.create_outbound_communication(
                dispute_id=dispute.id,
                recipient_email=vendor_email,
                subject=request.subject,
                body=request.body,
                sent_by=request.sent_by,
            )
        )

        await self.audit_log_service.create_audit_log(
            AuditLogCreatePayload(
                invoice_id=invoice_id,
                action="CLARIFICATION_SENT",
                old_status=current_status,
                new_status=current_status,
                remarks=self.AUDIT_REMARKS,
                performed_by=request.sent_by,
            ),
        )

        return SendClarificationResponse(
            invoice_id=invoice_id,
            dispute_id=dispute.id,
            communication_id=communication.id,
            vendor_email=vendor_email,
            message=self.SUCCESS_MESSAGE,
        )

    @staticmethod
    def _validate_invoice_eligibility(
        *,
        invoice_status: InvoiceStatus | None,
        validation_outcome: InvoiceValidationOutcome | None,
    ) -> str:
        if invoice_status == InvoiceStatus.READY_TO_PAY:
            raise ClarificationConflictError(
                "Clarification is not allowed for invoices ready to pay.",
            )

        if invoice_status == InvoiceStatus.REJECTED:
            raise ClarificationConflictError(
                "Clarification is not allowed for rejected invoices.",
            )

        if not is_eligible_for_clarification(
            invoice_status=invoice_status,
            validation_outcome=validation_outcome,
        ):
            raise ClarificationConflictError(
                "Invoice is not in an eligible state for clarification.",
            )

        return invoice_status.value
