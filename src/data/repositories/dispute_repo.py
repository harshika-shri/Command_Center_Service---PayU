from __future__ import annotations

from uuid import UUID

from src.data.models.postgres.disputes import Dispute
from src.data.models.postgres.enums import DisputeStatus
from src.data.repositories.base_repo import BaseRepository

_CLARIFICATION_REASON_CATEGORY = "vendor_clarification"


class DisputeRepository(BaseRepository):
    async def create_clarification_dispute(
        self,
        *,
        invoice_id: UUID,
        raised_by: UUID,
        summary: str,
    ) -> Dispute:
        dispute = Dispute(
            invoice_id=invoice_id,
            raised_by=raised_by,
            assigned_to=None,
            reason_category=_CLARIFICATION_REASON_CATEGORY,
            description=summary,
            status=DisputeStatus.OPEN,
        )
        self.session.add(
            dispute,
        )
        await self.session.flush()

        return dispute
