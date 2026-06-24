from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.clarification_exc import (
    ClarificationConflictError,
)
from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
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
from src.schemas.clarification_schema import (
    ClarificationDraftResponse,
)


class ClarificationDraftService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.clarification_repo = ClarificationRepository(
            session,
        )
        self.draft_builder = ClarificationDraftBuilder()

    async def generate_draft(
        self,
        invoice_id: UUID,
    ) -> ClarificationDraftResponse:
        context = await self.clarification_repo.get_draft_context(
            invoice_id,
        )

        if context is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        self._validate_invoice_eligibility(
            invoice_status=context.invoice.invoice_status,
            validation_outcome=context.validation_outcome,
        )

        clarification_points = self._resolve_clarification_points(
            context.vendor_clarifications,
            context.unresolved_issue_descriptions,
        )

        if not clarification_points:
            clarification_points = [
                "Additional clarification is required to complete invoice review.",
            ]

        invoice_reference = str(
            context.invoice.invoice_id,
        )
        subject = self.draft_builder.build_subject(
            context.invoice.invoice_number,
            invoice_reference,
        )
        body = self.draft_builder.build_body(
            context.invoice.invoice_number,
            invoice_reference,
            clarification_points,
        )

        return ClarificationDraftResponse(
            invoice_id=invoice_id,
            vendor_email=context.vendor_email,
            subject=subject,
            body=body,
            clarification_points=clarification_points,
        )

    @staticmethod
    def _validate_invoice_eligibility(
        *,
        invoice_status: InvoiceStatus | None,
        validation_outcome: InvoiceValidationOutcome | None,
    ) -> None:
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

    @staticmethod
    def _resolve_clarification_points(
        vendor_clarifications: list[str],
        unresolved_issue_descriptions: list[str],
    ) -> list[str]:
        if vendor_clarifications:
            return vendor_clarifications

        return unresolved_issue_descriptions
