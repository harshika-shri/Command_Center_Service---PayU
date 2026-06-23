from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.invoices import Invoice
from src.data.repositories.base_repo import BaseRepository


class InvoiceLookupRepository(BaseRepository):
    async def invoice_exists(
        self,
        invoice_id: UUID,
    ) -> bool:
        result = await self.execute(
            select(
                Invoice.id,
            ).where(
                Invoice.id == invoice_id,
            ),
        )

        return result.scalar_one_or_none() is not None
