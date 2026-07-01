from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
    ValidationIssueStatus,
)
from src.data.models.postgres.invoice_review_summaries import (
    InvoiceReviewSummary,
)
from src.data.models.postgres.invoice_validation_issues import (
    InvoiceValidationIssue,
)
from src.data.models.postgres.invoices import Invoice
from src.data.repositories.base_repo import BaseRepository
from src.data.repositories.invoice_recipient_repo import (
    InvoiceRecipientRepository,
)
from src.utils.vendor_issue_language import (
    deduplicate_issue_messages,
    vendor_friendly_issue_message,
)

_UNRESOLVED_ISSUE_STATUSES = (
    ValidationIssueStatus.OPEN,
    ValidationIssueStatus.PENDING_REVIEW,
)


@dataclass(frozen=True, slots=True)
class ClarificationInvoiceSnapshot:
    invoice_id: UUID
    invoice_number: str | None
    invoice_status: InvoiceStatus | None
    validation_outcome: InvoiceValidationOutcome | None


@dataclass(frozen=True, slots=True)
class ClarificationDraftContext:
    invoice: ClarificationInvoiceSnapshot
    vendor_email: str | None
    vendor_clarifications: list[str]
    open_issue_summaries: list[str]
    unresolved_issue_descriptions: list[str]
    unresolved_issue_messages: list[str]

    @property
    def validation_outcome(self) -> InvoiceValidationOutcome | None:
        return self.invoice.validation_outcome


class ClarificationRepository(BaseRepository):
    def __init__(
        self,
        session,
    ) -> None:
        super().__init__(session)
        self.recipient_repo = InvoiceRecipientRepository(session)

    async def get_draft_context(
        self,
        invoice_id: UUID,
    ) -> ClarificationDraftContext | None:
        invoice_result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_status,
                Invoice.validation_outcome,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        invoice_row = invoice_result.one_or_none()

        if invoice_row is None:
            return None

        vendor_email = await self.recipient_repo.get_recipient_email(
            invoice_id,
            sender_only=True,
        )
        vendor_clarifications = await self._get_vendor_clarifications(
            invoice_id,
        )
        open_issue_summaries = await self._get_open_issue_summaries(
            invoice_id,
        )
        unresolved_issues = await self._get_unresolved_issue_descriptions(
            invoice_id,
        )
        unresolved_issue_messages = (
            await self._get_unresolved_issue_messages(
                invoice_id,
            )
        )

        return ClarificationDraftContext(
            invoice=ClarificationInvoiceSnapshot(
                invoice_id=invoice_row.id,
                invoice_number=invoice_row.invoice_number,
                invoice_status=invoice_row.invoice_status,
                validation_outcome=invoice_row.validation_outcome,
            ),
            vendor_email=vendor_email,
            vendor_clarifications=vendor_clarifications,
            open_issue_summaries=open_issue_summaries,
            unresolved_issue_descriptions=unresolved_issues,
            unresolved_issue_messages=unresolved_issue_messages,
        )

    async def get_invoice_snapshot(
        self,
        invoice_id: UUID,
    ) -> ClarificationInvoiceSnapshot | None:
        result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_status,
                Invoice.validation_outcome,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return ClarificationInvoiceSnapshot(
            invoice_id=row.id,
            invoice_number=row.invoice_number,
            invoice_status=row.invoice_status,
            validation_outcome=row.validation_outcome,
        )

    async def get_vendor_email(
        self,
        invoice_id: UUID,
    ) -> str | None:
        return await self.recipient_repo.get_recipient_email(
            invoice_id,
            sender_only=True,
        )

    async def _get_vendor_clarifications(
        self,
        invoice_id: UUID,
    ) -> list[str]:
        result = await self.execute(
            select(
                InvoiceReviewSummary.vendor_clarifications_json,
            ).where(
                InvoiceReviewSummary.invoice_id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return []

        return self._normalize_clarification_points(
            row.vendor_clarifications_json,
        )

    async def _get_open_issue_summaries(
        self,
        invoice_id: UUID,
    ) -> list[str]:
        result = await self.execute(
            select(
                InvoiceReviewSummary.open_issues_json,
            ).where(
                InvoiceReviewSummary.invoice_id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return []

        return self._normalize_clarification_points(
            row.open_issues_json,
        )

    async def _get_unresolved_issue_messages(
        self,
        invoice_id: UUID,
    ) -> list[str]:
        result = await self.execute(
            select(
                InvoiceValidationIssue.check_name,
                InvoiceValidationIssue.description,
                InvoiceValidationIssue.issue_metadata,
            )
            .where(
                InvoiceValidationIssue.invoice_id == invoice_id,
                InvoiceValidationIssue.status.in_(
                    _UNRESOLVED_ISSUE_STATUSES,
                ),
            )
            .order_by(
                InvoiceValidationIssue.created_at.asc(),
            ),
        )

        messages = [
            vendor_friendly_issue_message(
                issue_code=ClarificationRepository._resolve_issue_code(
                    check_name=row.check_name,
                    issue_metadata=row.issue_metadata,
                ),
                description=row.description,
            )
            for row in result.all()
        ]

        return deduplicate_issue_messages(
            messages,
        )

    @staticmethod
    def _resolve_issue_code(
        *,
        check_name: str,
        issue_metadata: dict[str, Any] | None,
    ) -> str:
        if isinstance(
            issue_metadata,
            dict,
        ):
            issue_code = issue_metadata.get(
                "issue_code",
            )

            if isinstance(
                issue_code,
                str,
            ) and issue_code.strip():
                return issue_code

        return check_name

    async def _get_unresolved_issue_descriptions(
        self,
        invoice_id: UUID,
    ) -> list[str]:
        result = await self.execute(
            select(
                InvoiceValidationIssue.description,
            )
            .where(
                InvoiceValidationIssue.invoice_id == invoice_id,
                InvoiceValidationIssue.status.in_(
                    _UNRESOLVED_ISSUE_STATUSES,
                ),
            )
            .order_by(
                InvoiceValidationIssue.created_at.asc(),
            ),
        )

        return list(
            result.scalars().all(),
        )

    @staticmethod
    def _normalize_clarification_points(
        raw_points: list[Any],
    ) -> list[str]:
        points: list[str] = []

        for item in raw_points:
            if isinstance(
                item,
                str,
            ):
                normalized = item.strip()

                if normalized:
                    points.append(
                        normalized,
                    )

                continue

            if isinstance(
                item,
                dict,
            ):
                for key in (
                    "message",
                    "description",
                    "text",
                    "point",
                ):
                    value = item.get(
                        key,
                    )

                    if isinstance(
                        value,
                        str,
                    ):
                        normalized = value.strip()

                        if normalized:
                            points.append(
                                normalized,
                            )

                        break

        return points
