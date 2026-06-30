from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecentMailItem(BaseModel):
    message_id: str
    mailbox: str | None = None
    subject: str | None = None
    received_from: str | None = None
    attachment_filename: str | None = None
    processed_at: datetime
    has_invoice: bool
    mail_status: str
    invoice_id: UUID | None = None


class RecentMailListResponse(BaseModel):
    items: list[RecentMailItem]
    total: int = Field(
        ge=0,
    )
