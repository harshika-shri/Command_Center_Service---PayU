from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from src.data.models.postgres.dispute_communications import (
    DisputeCommunication,
)
from src.data.models.postgres.enums import CommunicationStatus
from src.data.repositories.base_repo import BaseRepository


class DisputeCommunicationRepository(BaseRepository):
    async def create_outbound_communication(
        self,
        *,
        dispute_id: UUID,
        recipient_email: str,
        subject: str,
        body: str,
        sent_by: UUID,
    ) -> DisputeCommunication:
        communication = DisputeCommunication(
            dispute_id=dispute_id,
            drafted_by_ai=False,
            reviewed_by=sent_by,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
            status=CommunicationStatus.SENT,
            sent_at=datetime.now(
                UTC,
            ),
        )
        self.session.add(
            communication,
        )
        await self.session.flush()

        return communication
