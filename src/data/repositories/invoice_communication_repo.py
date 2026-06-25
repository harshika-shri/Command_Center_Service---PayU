from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.dispute_communications import (
    DisputeCommunication,
)
from src.data.models.postgres.disputes import Dispute
from src.data.models.postgres.users import User
from src.data.repositories.base_repo import BaseRepository

_CLARIFICATION_CATEGORY = "vendor_clarification"
_REJECTION_CATEGORY = "vendor_rejection"


@dataclass(frozen=True, slots=True)
class DisputeHistoryRow:
    dispute_id: UUID
    reason_category: str
    status: str
    description: str | None
    raised_by_id: UUID
    raised_by_name: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CommunicationHistoryRow:
    communication_id: UUID
    dispute_id: UUID
    communication_type: str
    reason_category: str
    subject: str
    body: str
    recipient_email: str
    status: str
    sent_at: datetime | None
    sent_by_id: UUID | None
    sent_by_name: str | None
    created_at: datetime


class InvoiceCommunicationRepository(BaseRepository):
    async def list_disputes_by_invoice(
        self,
        invoice_id: UUID,
    ) -> list[DisputeHistoryRow]:
        result = await self.execute(
            select(
                Dispute.id,
                Dispute.reason_category,
                Dispute.status,
                Dispute.description,
                Dispute.raised_by,
                User.name,
                Dispute.created_at,
            )
            .join(
                User,
                Dispute.raised_by == User.id,
            )
            .where(
                Dispute.invoice_id == invoice_id,
            )
            .order_by(
                Dispute.created_at.desc(),
            ),
        )

        return [
            DisputeHistoryRow(
                dispute_id=row.id,
                reason_category=row.reason_category,
                status=row.status.value,
                description=row.description,
                raised_by_id=row.raised_by,
                raised_by_name=row.name,
                created_at=row.created_at,
            )
            for row in result.all()
        ]

    async def list_communication_history(
        self,
        invoice_id: UUID,
    ) -> list[CommunicationHistoryRow]:
        result = await self.execute(
            select(
                DisputeCommunication.id,
                DisputeCommunication.dispute_id,
                Dispute.reason_category,
                DisputeCommunication.subject,
                DisputeCommunication.body,
                DisputeCommunication.recipient_email,
                DisputeCommunication.status,
                DisputeCommunication.sent_at,
                DisputeCommunication.reviewed_by,
                User.name,
                DisputeCommunication.created_at,
            )
            .join(
                Dispute,
                DisputeCommunication.dispute_id == Dispute.id,
            )
            .outerjoin(
                User,
                DisputeCommunication.reviewed_by == User.id,
            )
            .where(
                Dispute.invoice_id == invoice_id,
            )
            .order_by(
                DisputeCommunication.sent_at.desc().nullslast(),
                DisputeCommunication.created_at.desc(),
            ),
        )

        return [
            CommunicationHistoryRow(
                communication_id=row.id,
                dispute_id=row.dispute_id,
                communication_type=self._communication_type(
                    row.reason_category,
                ),
                reason_category=row.reason_category,
                subject=row.subject,
                body=row.body,
                recipient_email=row.recipient_email,
                status=row.status.value,
                sent_at=row.sent_at,
                sent_by_id=row.reviewed_by,
                sent_by_name=row.name,
                created_at=row.created_at,
            )
            for row in result.all()
        ]

    @staticmethod
    def _communication_type(
        reason_category: str,
    ) -> str:
        if reason_category == _REJECTION_CATEGORY:
            return "rejection"

        if reason_category == _CLARIFICATION_CATEGORY:
            return "clarification"

        return reason_category
