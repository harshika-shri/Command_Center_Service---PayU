from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ClarificationDraftResponse(BaseModel):
    invoice_id: UUID
    vendor_email: str | None
    subject: str
    body: str
    clarification_points: list[str]


class SendClarificationRequest(BaseModel):
    sent_by: UUID
    subject: str = Field(
        min_length=1,
    )
    body: str = Field(
        min_length=1,
    )


class SendClarificationResponse(BaseModel):
    invoice_id: UUID
    dispute_id: UUID
    communication_id: UUID
    vendor_email: str
    message: str
