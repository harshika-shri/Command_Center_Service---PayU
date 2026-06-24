from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update

from src.data.models.postgres.disputes import Dispute
from src.data.models.postgres.enums import (
    DisputeStatus,
    InvoiceStatus,
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

_REJECTION_DISPUTE_CATEGORY = "vendor_rejection"


@dataclass(frozen=True, slots=True)
class RejectionInvoiceSnapshot:
    invoice_id: UUID
    invoice_number: str | None
    invoice_status: InvoiceStatus | None
    rejection_reason: str | None


@dataclass(frozen=True, slots=True)
class RejectionIssueRecord:
    issue_code: str
    description: str


@dataclass(frozen=True, slots=True)
class RejectionDraftContext:
    invoice: RejectionInvoiceSnapshot
    vendor_email: str | None
    rejection_reason: str | None
    executive_summary: str | None
    issues: list[RejectionIssueRecord]


class RejectionRepository(BaseRepository):
    async def get_invoice_for_update(
        self,
        invoice_id: UUID,
    ) -> RejectionInvoiceSnapshot | None:
        result = await self.execute(
            select(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .with_for_update(),
        )
        invoice = result.scalar_one_or_none()

        if invoice is None:
            return None

        return RejectionInvoiceSnapshot(
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number,
            invoice_status=invoice.invoice_status,
            rejection_reason=invoice.rejection_reason,
        )

    async def reject_invoice(
        self,
        invoice_id: UUID,
        rejection_reason: str,
    ) -> None:
        await self.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .values(
                invoice_status=InvoiceStatus.REJECTED,
                rejection_reason=rejection_reason,
            ),
        )

    async def get_rejection_draft_context(
        self,
        invoice_id: UUID,
    ) -> RejectionDraftContext | None:
        invoice_result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_status,
                Invoice.rejection_reason,
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

        executive_summary = await self._get_executive_summary(
            invoice_id,
        )
        issues = await self._get_validation_issues(
            invoice_id,
        )

        return RejectionDraftContext(
            invoice=RejectionInvoiceSnapshot(
                invoice_id=invoice_row.id,
                invoice_number=invoice_row.invoice_number,
                invoice_status=invoice_row.invoice_status,
                rejection_reason=invoice_row.rejection_reason,
            ),
            vendor_email=self._resolve_vendor_email(
                invoice_row.email,
                invoice_row.vendor_email,
            ),
            rejection_reason=invoice_row.rejection_reason,
            executive_summary=executive_summary,
            issues=issues,
        )

    async def get_invoice_snapshot(
        self,
        invoice_id: UUID,
    ) -> RejectionInvoiceSnapshot | None:
        result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_status,
                Invoice.rejection_reason,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return RejectionInvoiceSnapshot(
            invoice_id=row.id,
            invoice_number=row.invoice_number,
            invoice_status=row.invoice_status,
            rejection_reason=row.rejection_reason,
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

    async def get_or_create_rejection_dispute(
        self,
        *,
        invoice_id: UUID,
        raised_by: UUID,
        summary: str,
    ) -> Dispute:
        existing_result = await self.execute(
            select(Dispute)
            .where(
                Dispute.invoice_id == invoice_id,
                Dispute.status == DisputeStatus.OPEN,
            )
            .order_by(
                Dispute.created_at.desc(),
            )
            .limit(
                1,
            ),
        )
        existing_dispute = existing_result.scalar_one_or_none()

        if existing_dispute is not None:
            return existing_dispute

        dispute = Dispute(
            invoice_id=invoice_id,
            raised_by=raised_by,
            assigned_to=None,
            reason_category=_REJECTION_DISPUTE_CATEGORY,
            description=summary,
            status=DisputeStatus.OPEN,
        )
        self.session.add(
            dispute,
        )
        await self.session.flush()

        return dispute

    async def _get_executive_summary(
        self,
        invoice_id: UUID,
    ) -> str | None:
        result = await self.execute(
            select(
                InvoiceReviewSummary.executive_summary,
            ).where(
                InvoiceReviewSummary.invoice_id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return row.executive_summary

    async def _get_validation_issues(
        self,
        invoice_id: UUID,
    ) -> list[RejectionIssueRecord]:
        result = await self.execute(
            select(
                InvoiceValidationIssue.check_name,
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

        return [
            RejectionIssueRecord(
                issue_code=row.check_name,
                description=row.description,
            )
            for row in result.all()
        ]

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
