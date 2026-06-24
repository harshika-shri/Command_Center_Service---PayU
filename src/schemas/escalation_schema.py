from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class EscalateInvoiceRequest(BaseModel):
    escalated_by: UUID
    manager_id: UUID
    reason: str = Field(
        min_length=1,
    )


class EscalateInvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_status: str
    escalated_to: UUID
    message: str
