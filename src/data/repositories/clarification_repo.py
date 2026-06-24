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
from src.data.models.postgres.invoice_extracted_vendor import (
    InvoiceExtractedVendor,
)
from src.data.models.postgres.invoice_review_summaries import (
    InvoiceReviewSummary,
)
from src.data.models.postgres.invoice_validation_issues import (
    InvoiceValidationIssue,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository

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
    unresolved_issue_descriptions: list[str]

    @property
    def validation_outcome(self) -> InvoiceValidationOutcome | None:
        return self.invoice.validation_outcome


class ClarificationRepository(BaseRepository):
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
                Invoice.vendor_id,
                VendorMaster.email,
                InvoiceExtractedVendor.vendor_email,
            )
            .select_from(
                Invoice,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .outerjoin(
                InvoiceExtractedVendor,
                Invoice.id == InvoiceExtractedVendor.invoice_id,
            )
            .where(
                Invoice.id == invoice_id,
            ),
        )
        invoice_row = invoice_result.one_or_none()

        if invoice_row is None:
            return None

        vendor_email = self._resolve_vendor_email(
            invoice_row.email,
            invoice_row.vendor_email,
        )
        vendor_clarifications = await self._get_vendor_clarifications(
            invoice_id,
        )
        unresolved_issues = await self._get_unresolved_issue_descriptions(
            invoice_id,
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
            unresolved_issue_descriptions=unresolved_issues,
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
        result = await self.execute(
            select(
                VendorMaster.email,
                InvoiceExtractedVendor.vendor_email,
            )
            .select_from(
                Invoice,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .outerjoin(
                InvoiceExtractedVendor,
                Invoice.id == InvoiceExtractedVendor.invoice_id,
            )
            .where(
                Invoice.id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return self._resolve_vendor_email(
            row.email,
            row.vendor_email,
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
    def _resolve_vendor_email(
        vendor_master_email: str | None,
        extracted_vendor_email: str | None,
    ) -> str | None:
        if vendor_master_email:
            return vendor_master_email

        if extracted_vendor_email:
            return extracted_vendor_email

        return None

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
