from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.postgres.dispute_communications import (
    DisputeCommunication,
)
from src.data.repositories.dispute_communication_repo import (
    DisputeCommunicationRepository,
)


class DisputeCommunicationService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.communication_repo = DisputeCommunicationRepository(
            session,
        )

    async def create_outbound_communication(
        self,
        *,
        dispute_id: UUID,
        recipient_email: str,
        subject: str,
        body: str,
        sent_by: UUID,
    ) -> DisputeCommunication:
        return await self.communication_repo.create_outbound_communication(
            dispute_id=dispute_id,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            sent_by=sent_by,
        )
