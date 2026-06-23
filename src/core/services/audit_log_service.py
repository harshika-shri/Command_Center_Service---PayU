from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.repositories.audit_log_repo import (
    AuditLogRepository,
)


@dataclass(frozen=True, slots=True)
class AuditLogCreatePayload:
    invoice_id: UUID
    action: str
    old_status: str | None
    new_status: str | None
    remarks: str | None


class AuditLogService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.audit_log_repo = AuditLogRepository(
            session,
        )

    async def create_audit_log(
        self,
        payload: AuditLogCreatePayload,
    ) -> None:
        await self.audit_log_repo.create(
            invoice_id=payload.invoice_id,
            action=payload.action,
            old_status=payload.old_status,
            new_status=payload.new_status,
            remarks=payload.remarks,
        )

    @staticmethod
    def format_invoice_status(
        invoice_status: InvoiceStatus | None,
    ) -> str | None:
        if invoice_status is None:
            return None

        return invoice_status.value

    @staticmethod
    def format_validation_outcome(
        validation_outcome: InvoiceValidationOutcome | None,
    ) -> str | None:
        if validation_outcome is None:
            return None

        return validation_outcome.value
