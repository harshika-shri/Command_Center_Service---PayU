from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.data.models.postgres.enums import (
    InvoiceValidationOutcome,
)


class ValidationEventOutcome(str, Enum):
    RESOLVED = "resolved"
    RECOVERED = "recovered"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
    DUPLICATE = "duplicate"


_LEGACY_OUTCOME_MAP = {
    "approved": "resolved",
    "pending_review": "recovered",
    "rejected": "unresolved",
}


class ValidationCompletedEvent(BaseModel):
    invoice_id: UUID
    event_type: str
    validation_outcome: ValidationEventOutcome

    @field_validator(
        "validation_outcome",
        mode="before",
    )
    @classmethod
    def normalize_validation_outcome(
        cls,
        value: object,
    ) -> object:
        if isinstance(
            value,
            str,
        ):
            normalized = value.lower()
            return _LEGACY_OUTCOME_MAP.get(
                normalized,
                normalized,
            )

        return value
