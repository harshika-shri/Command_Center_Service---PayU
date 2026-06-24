from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.rejection_exc import (
    InvoiceRejectionConflictError,
    RejectionDraftGenerationError,
)
from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.rejection_llm_service import (
    RejectionLlmService,
)
from src.core.workflow.invoice_workflow_buckets import (
    is_rejected_for_vendor_communication,
)
from src.core.workflow.rejection_draft_builder import (
    RejectionDraftBuilder,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
)
from src.data.repositories.rejection_repo import (
    RejectionIssueRecord,
    RejectionRepository,
)
from src.schemas.rejection_schema import (
    RejectionDraftResponse,
)
from src.utils.vendor_issue_language import (
    deduplicate_issue_messages,
    vendor_friendly_issue_message,
)


class RejectionDraftService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.rejection_repo = RejectionRepository(
            session,
        )
        self.draft_builder = RejectionDraftBuilder()
        self.llm_service = RejectionLlmService()

    async def generate_draft(
        self,
        invoice_id: UUID,
    ) -> RejectionDraftResponse:
        context = await self.rejection_repo.get_rejection_draft_context(
            invoice_id,
        )

        if context is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        self._validate_invoice_eligibility(
            context.invoice.invoice_status,
        )

        issues = self._translate_issues(
            context.issues,
        )

        if not issues:
            issues = [
                (
                    "The submitted invoice could not be approved based on "
                    "our review findings."
                ),
            ]

        invoice_reference = (
            context.invoice.invoice_number
            or str(
                context.invoice.invoice_id,
            )
        )

        try:
            generated = self.llm_service.generate_rejection_email(
                invoice_number=invoice_reference,
                rejection_reason=context.rejection_reason,
                issues=issues,
                executive_summary=context.executive_summary,
            )
            subject = generated["subject"]
            body = generated["body"]
        except RejectionDraftGenerationError:
            subject = self.draft_builder.build_subject(
                context.invoice.invoice_number,
                str(
                    context.invoice.invoice_id,
                ),
            )
            body = self.draft_builder.build_body(
                context.invoice.invoice_number,
                str(
                    context.invoice.invoice_id,
                ),
                issues,
                context.rejection_reason,
            )

        return RejectionDraftResponse(
            invoice_id=invoice_id,
            vendor_email=context.vendor_email,
            subject=subject,
            body=body,
            issues=issues,
        )

    @staticmethod
    def _validate_invoice_eligibility(
        invoice_status: InvoiceStatus | None,
    ) -> None:
        if not is_rejected_for_vendor_communication(
            invoice_status,
        ):
            raise InvoiceRejectionConflictError(
                "Rejection draft is only available for rejected invoices.",
            )

    @staticmethod
    def _translate_issues(
        issues: list[RejectionIssueRecord],
    ) -> list[str]:
        translated = [
            vendor_friendly_issue_message(
                issue_code=issue.issue_code,
                description=issue.description,
            )
            for issue in issues
        ]

        return deduplicate_issue_messages(
            translated,
        )
