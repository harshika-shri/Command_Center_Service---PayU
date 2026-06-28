from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select, update

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository

_OVERDUE_ELIGIBLE_STATUSES = (
    InvoiceStatus.UNDER_REVIEW,
    InvoiceStatus.READY_FOR_APPROVAL,
    InvoiceStatus.READY_TO_PAY,
    InvoiceStatus.ESCALATED,
    InvoiceStatus.PARTIALLY_APPROVED,
)


@dataclass(frozen=True, slots=True)
class OverdueCandidateRow:
    invoice_id: UUID
    invoice_number: str | None
    due_date: date
    vendor_name: str | None
    previous_status: str
    validation_outcome: InvoiceValidationOutcome | None


class OverdueInvoiceRepository(BaseRepository):
    async def fetch_invoices_to_mark_overdue(
        self,
        today: date,
    ) -> list[OverdueCandidateRow]:
        result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.due_date,
                Invoice.invoice_status,
                Invoice.validation_outcome,
                VendorMaster.vendor_name,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .where(
                Invoice.due_date.is_not(
                    None,
                ),
                Invoice.due_date < today,
                Invoice.invoice_status.in_(
                    _OVERDUE_ELIGIBLE_STATUSES,
                ),
            ),
        )

        rows: list[OverdueCandidateRow] = []

        for row in result.all():
            if row.due_date is None or row.invoice_status is None:
                continue

            rows.append(
                OverdueCandidateRow(
                    invoice_id=row.id,
                    invoice_number=row.invoice_number,
                    due_date=row.due_date,
                    vendor_name=row.vendor_name,
                    previous_status=row.invoice_status.value,
                    validation_outcome=row.validation_outcome,
                ),
            )

        return rows

    async def mark_invoices_overdue(
        self,
        invoice_ids: list[UUID],
    ) -> None:
        if not invoice_ids:
            return

        await self.session.execute(
            update(
                Invoice,
            )
            .where(
                Invoice.id.in_(
                    invoice_ids,
                ),
                Invoice.invoice_status.in_(
                    _OVERDUE_ELIGIBLE_STATUSES,
                ),
            )
            .values(
                invoice_status=InvoiceStatus.OVERDUE,
            ),
        )
        await self.session.flush()
