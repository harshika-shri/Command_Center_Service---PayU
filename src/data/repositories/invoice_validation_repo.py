from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.invoice_review_summaries import (
    InvoiceReviewSummary,
)
from src.data.models.postgres.invoice_validation_issues import (
    InvoiceValidationIssue,
)
from src.data.models.postgres.invoices import Invoice
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class ValidationIssueRow:
    id: UUID
    check_stage: str
    check_name: str
    field_name: str | None
    issue_type: str
    expected_value: str | None
    actual_value: str | None
    description: str
    status: str
    metadata: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ReviewSummaryRow:
    decision: str
    executive_summary: str
    system_recoveries_json: list[Any]
    open_issues_json: list[Any]
    vendor_clarifications_json: list[Any]
    validation_steps_json: dict[str, str]
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class InvoiceValidationData:
    validation_outcome: str | None
    issues: list[ValidationIssueRow]
    review_summary: ReviewSummaryRow | None


class InvoiceValidationRepository(BaseRepository):
    async def get_validation_data(
        self,
        invoice_id: UUID,
    ) -> InvoiceValidationData | None:
        outcome_result = await self.execute(
            select(
                Invoice.validation_outcome,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        outcome_row = outcome_result.one_or_none()

        if outcome_row is None:
            return None

        issues = await self._get_issues(
            invoice_id,
        )
        review_summary = await self._get_review_summary(
            invoice_id,
        )

        return InvoiceValidationData(
            validation_outcome=(
                outcome_row.validation_outcome.value
                if outcome_row.validation_outcome is not None
                else None
            ),
            issues=issues,
            review_summary=review_summary,
        )

    async def _get_issues(
        self,
        invoice_id: UUID,
    ) -> list[ValidationIssueRow]:
        result = await self.execute(
            select(InvoiceValidationIssue)
            .where(
                InvoiceValidationIssue.invoice_id == invoice_id,
            )
            .order_by(
                InvoiceValidationIssue.created_at.asc(),
            ),
        )

        return [
            ValidationIssueRow(
                id=issue.id,
                check_stage=issue.check_stage,
                check_name=issue.check_name,
                field_name=issue.field_name,
                issue_type=issue.issue_type.value,
                expected_value=issue.expected_value,
                actual_value=issue.actual_value,
                description=issue.description,
                status=issue.status.value,
                metadata=issue.issue_metadata,
            )
            for issue in result.scalars().all()
        ]

    async def _get_review_summary(
        self,
        invoice_id: UUID,
    ) -> ReviewSummaryRow | None:
        result = await self.execute(
            select(InvoiceReviewSummary).where(
                InvoiceReviewSummary.invoice_id == invoice_id,
            ),
        )
        summary = result.scalar_one_or_none()

        if summary is None:
            return None

        return ReviewSummaryRow(
            decision=summary.decision,
            executive_summary=summary.executive_summary,
            system_recoveries_json=summary.system_recoveries_json,
            open_issues_json=summary.open_issues_json,
            vendor_clarifications_json=summary.vendor_clarifications_json,
            validation_steps_json=dict(
                getattr(
                    summary,
                    "validation_steps_json",
                    {},
                )
                or {},
            ),
            generated_at=summary.generated_at,
        )
