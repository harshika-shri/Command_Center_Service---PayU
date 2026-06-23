from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ApproveInvoiceRequest(BaseModel):
    approved_by: UUID
    comments: str | None = None


class ApproveInvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_status: str
    message: str
