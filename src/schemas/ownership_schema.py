from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class TakeOwnershipRequest(BaseModel):
    manager_id: UUID


class TakeOwnershipResponse(BaseModel):
    invoice_id: UUID
    assigned_manager_id: UUID
    message: str
