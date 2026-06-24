from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RejectInvoiceRequest(BaseModel):
    rejected_by: UUID
    rejection_reason: str = Field(
        min_length=1,
    )


class RejectInvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_status: str
    message: str


class RejectionDraftResponse(BaseModel):
    invoice_id: UUID
    vendor_email: str | None
    subject: str
    body: str
    issues: list[str]


class SendRejectionEmailRequest(BaseModel):
    sent_by: UUID
    subject: str = Field(
        min_length=1,
    )
    body: str = Field(
        min_length=1,
    )


class SendRejectionEmailResponse(BaseModel):
    invoice_id: UUID
    communication_id: UUID
    vendor_email: str
    message: str
