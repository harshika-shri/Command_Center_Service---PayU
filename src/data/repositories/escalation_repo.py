from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select, update

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
    UserRole,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.users import User
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class InvoiceEscalationSnapshot:
    invoice_id: UUID
    invoice_status: InvoiceStatus | None
    validation_outcome: InvoiceValidationOutcome | None
    escalated_to: UUID | None


@dataclass(frozen=True, slots=True)
class FinanceManagerSnapshot:
    manager_id: UUID
    name: str
    email: str


class EscalationRepository(BaseRepository):
    async def get_invoice_for_update(
        self,
        invoice_id: UUID,
    ) -> InvoiceEscalationSnapshot | None:
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

        return InvoiceEscalationSnapshot(
            invoice_id=invoice.id,
            invoice_status=invoice.invoice_status,
            validation_outcome=invoice.validation_outcome,
            escalated_to=invoice.escalated_to,
        )

    async def get_finance_manager(
        self,
        manager_id: UUID,
    ) -> FinanceManagerSnapshot | None:
        result = await self.execute(
            select(
                User.id,
                User.name,
                User.email,
                User.role,
                User.is_active,
            ).where(
                User.id == manager_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        if row.role != UserRole.FINANCE_MANAGER or not row.is_active:
            return None

        return FinanceManagerSnapshot(
            manager_id=row.id,
            name=row.name,
            email=row.email,
        )

    async def escalate_invoice(
        self,
        invoice_id: UUID,
        manager_id: UUID,
    ) -> None:
        await self.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .values(
                invoice_status=InvoiceStatus.ESCALATED,
                escalated_to=manager_id,
                assigned_manager_id=manager_id,
                assigned_at=func.now(),
            ),
        )
