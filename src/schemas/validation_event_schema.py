from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class ValidationEventOutcome(str, Enum):
    APPROVED = "APPROVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"


class ValidationCompletedEvent(BaseModel):
    invoice_id: UUID
    event_type: str
    validation_outcome: ValidationEventOutcome
