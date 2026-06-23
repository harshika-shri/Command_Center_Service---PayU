from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.invoice_access_service import (
    InvoiceAccessService,
)
from src.data.repositories.invoice_validation_repo import (
    InvoiceValidationData,
    InvoiceValidationRepository,
)
from src.schemas.invoice_review_schema import (
    InvoiceValidationResponse,
    ReviewSummaryDetails,
    ValidationIssueDetails,
)


class InvoiceValidationDetailService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.access_service = InvoiceAccessService(
            session,
        )
        self.validation_repo = InvoiceValidationRepository(
            session,
        )

    async def get_validation(
        self,
        invoice_id: UUID,
        *,
        require_exists: bool = True,
    ) -> InvoiceValidationResponse:
        if require_exists:
            await self.access_service.ensure_invoice_exists(
                invoice_id,
            )

        data = await self.validation_repo.get_validation_data(
            invoice_id,
        )

        if data is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        return self._map_validation(
            data,
        )

    @staticmethod
    def _map_validation(
        data: InvoiceValidationData,
    ) -> InvoiceValidationResponse:
        review_summary = None

        if data.review_summary is not None:
            review_summary = ReviewSummaryDetails(
                decision=data.review_summary.decision,
                executive_summary=data.review_summary.executive_summary,
                system_recoveries_json=data.review_summary.system_recoveries_json,
                open_issues_json=data.review_summary.open_issues_json,
                vendor_clarifications_json=data.review_summary.vendor_clarifications_json,
                generated_at=data.review_summary.generated_at,
            )

        return InvoiceValidationResponse(
            validation_outcome=data.validation_outcome,
            issues=[
                ValidationIssueDetails(
                    id=issue.id,
                    check_stage=issue.check_stage,
                    check_name=issue.check_name,
                    field_name=issue.field_name,
                    issue_type=issue.issue_type,
                    expected_value=issue.expected_value,
                    actual_value=issue.actual_value,
                    description=issue.description,
                    status=issue.status,
                    metadata=issue.metadata,
                )
                for issue in data.issues
            ],
            review_summary=review_summary,
        )
