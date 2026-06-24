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
from src.core.services.dispute_communication_service import (
    DisputeCommunicationService,
)
from src.core.services.sendgrid_service import (
    SendGridService,
)
from src.core.workflow.clarification_draft_builder import (
    ClarificationDraftBuilder,
)
from src.core.workflow.invoice_workflow_buckets import (
    is_rejected_for_vendor_communication,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
)
from src.data.repositories.rejection_repo import (
    RejectionRepository,
)
from src.schemas.rejection_schema import (
    SendRejectionEmailRequest,
    SendRejectionEmailResponse,
)


class RejectionEmailService:
    SUCCESS_MESSAGE = "Rejection email sent to vendor."
    AUDIT_REMARKS = "Vendor rejection communication sent."

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.rejection_repo = RejectionRepository(
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
        self.html_builder = ClarificationDraftBuilder()

    async def send_rejection_email(
        self,
        invoice_id: UUID,
        request: SendRejectionEmailRequest,
    ) -> SendRejectionEmailResponse:
        snapshot = await self.rejection_repo.get_invoice_snapshot(
            invoice_id,
        )

        if snapshot is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        current_status = self._validate_invoice_eligibility(
            snapshot.invoice_status,
        )

        vendor_email = await self.rejection_repo.get_vendor_email(
            invoice_id,
        )

        if not vendor_email:
            raise InvoiceRejectionValidationError(
                "Vendor email unavailable.",
            )

        html_content = self.html_builder.plain_text_to_html(
            request.body,
        )

        self.sendgrid_service.send_email(
            to_email=vendor_email,
            subject=request.subject,
            html_content=html_content,
        )

        dispute = await self.rejection_repo.get_or_create_rejection_dispute(
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
                action="REJECTION_EMAIL_SENT",
                old_status=current_status,
                new_status=current_status,
                remarks=self.AUDIT_REMARKS,
                performed_by=request.sent_by,
            ),
        )

        return SendRejectionEmailResponse(
            invoice_id=invoice_id,
            communication_id=communication.id,
            vendor_email=vendor_email,
            message=self.SUCCESS_MESSAGE,
        )

    @staticmethod
    def _validate_invoice_eligibility(
        invoice_status: InvoiceStatus | None,
    ) -> str:
        if not is_rejected_for_vendor_communication(
            invoice_status,
        ):
            raise InvoiceRejectionConflictError(
                "Rejection email can only be sent for rejected invoices.",
            )

        return invoice_status.value
