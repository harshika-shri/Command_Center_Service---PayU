from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.disputes import Dispute
from src.data.repositories.dispute_repo import DisputeRepository


class DisputeService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.dispute_repo = DisputeRepository(
            session,
        )

    async def create_clarification_dispute(
        self,
        *,
        invoice_id: UUID,
        raised_by: UUID,
        summary: str,
    ) -> Dispute:
        return await self.dispute_repo.create_clarification_dispute(
            invoice_id=invoice_id,
            raised_by=raised_by,
            summary=summary,
        )
