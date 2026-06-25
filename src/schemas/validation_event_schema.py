from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

from src.constants.redis_stream_constants import (
    VALIDATION_EVENT_TYPE_COMPLETED,
    VALIDATION_EVENT_TYPE_PENDING_REVIEW,
    VALIDATION_EVENT_TYPE_REJECTED,
)

VALIDATION_EVENT_VERSION = 1

_SUPPORTED_EVENT_TYPES = frozenset(
    {
        VALIDATION_EVENT_TYPE_COMPLETED,
        VALIDATION_EVENT_TYPE_PENDING_REVIEW,
        VALIDATION_EVENT_TYPE_REJECTED,
    },
)


class ValidationCompletedEvent(BaseModel):
    version: int
    event_type: str
    invoice_id: UUID
    occurred_at: datetime

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
