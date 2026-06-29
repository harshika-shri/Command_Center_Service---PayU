from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.constants.redis_stream_constants import (
    VALIDATION_EVENT_TYPES,
)

VALIDATION_EVENT_VERSION = 1

_LEGACY_EVENT_TYPES = frozenset(
    {
        "validation.completed",
        "validation.pending_review",
        "validation.rejected",
    },
)

_SUPPORTED_EVENT_TYPES = VALIDATION_EVENT_TYPES | _LEGACY_EVENT_TYPES


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
    version: int
    event_type: str
    invoice_id: UUID
    occurred_at: datetime
    validation_outcome: ValidationEventOutcome

    @field_validator(
        "version",
        mode="before",
    )
    @classmethod
    def parse_version(
        cls,
        value: object,
    ) -> int:
        return int(
            value,
        )

    @field_validator(
        "event_type",
    )
    @classmethod
    def validate_event_type(
        cls,
        value: str,
    ) -> str:
        if value not in _SUPPORTED_EVENT_TYPES:
            raise ValueError(
                f"Unsupported event_type: {value}",
            )

        return value

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

    @field_validator(
        "occurred_at",
        mode="before",
    )
    @classmethod
    def parse_occurred_at(
        cls,
        value: object,
    ) -> datetime:
        if isinstance(
            value,
            datetime,
        ):
            return value

        return datetime.fromisoformat(
            str(
                value,
            ),
        )
