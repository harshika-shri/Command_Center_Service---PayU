from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.data.repositories.invoice_lookup_repo import (
    InvoiceLookupRepository,
)


class InvoiceAccessService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.lookup_repo = InvoiceLookupRepository(
            session,
        )

    async def ensure_invoice_exists(
        self,
        invoice_id: UUID,
    ) -> None:
        exists = await self.lookup_repo.invoice_exists(
            invoice_id,
        )

        if not exists:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )
