from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select, update

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.models.postgres.invoices import Invoice
from src.data.repositories.base_repo import BaseRepository

_POST_VALIDATION_TERMINAL_STATUSES = (
    InvoiceStatus.REJECTED,
    InvoiceStatus.READY_TO_PAY,
    InvoiceStatus.PAID,
    InvoiceStatus.ESCALATED,
    InvoiceStatus.OVERDUE,
)


@dataclass(frozen=True, slots=True)
class InvoiceWorkflowSnapshot:
    invoice_id: UUID
    invoice_status: InvoiceStatus | None
    validation_outcome: InvoiceValidationOutcome | None


class InvoiceRepository(BaseRepository):
    async def get_workflow_snapshot(
        self,
        invoice_id: UUID,
    ) -> InvoiceWorkflowSnapshot | None:
        result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_status,
                Invoice.validation_outcome,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return InvoiceWorkflowSnapshot(
            invoice_id=row.id,
            invoice_status=row.invoice_status,
            validation_outcome=row.validation_outcome,
        )

    async def update_invoice_status(
        self,
        invoice_id: UUID,
        *,
        invoice_status: InvoiceStatus,
    ) -> None:
        await self.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .values(
                invoice_status=invoice_status,
            ),
        )

    async def update_workflow_state(
        self,
        invoice_id: UUID,
        *,
        invoice_status: InvoiceStatus,
        validation_outcome: InvoiceValidationOutcome,
    ) -> None:
        await self.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .values(
                invoice_status=invoice_status,
                validation_outcome=validation_outcome,
            ),
        )

    async def find_validated_invoices_missing_under_review(
        self,
    ) -> list[InvoiceWorkflowSnapshot]:
        result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_status,
                Invoice.validation_outcome,
            ).where(
                Invoice.validation_outcome.is_not(
                    None,
                ),
                or_(
                    Invoice.invoice_status.is_(
                        None,
                    ),
                    Invoice.invoice_status.not_in(
                        _POST_VALIDATION_TERMINAL_STATUSES
                        + (InvoiceStatus.UNDER_REVIEW,),
                    ),
                ),
            ),
        )

        return [
            InvoiceWorkflowSnapshot(
                invoice_id=row.id,
                invoice_status=row.invoice_status,
                validation_outcome=row.validation_outcome,
            )
            for row in result.all()
        ]
