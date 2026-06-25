from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from src.constants.redis_stream_constants import (
    VALIDATION_EVENT_TYPE_COMPLETED,
    VALIDATION_EVENT_TYPE_PENDING_REVIEW,
    VALIDATION_EVENT_TYPE_REJECTED,
)
from src.schemas.validation_event_schema import (
    VALIDATION_EVENT_VERSION,
    ValidationCompletedEvent,
)

_LEGACY_OUTCOME_TO_EVENT_TYPE = {
    "APPROVED": VALIDATION_EVENT_TYPE_COMPLETED,
    "PENDING_REVIEW": VALIDATION_EVENT_TYPE_PENDING_REVIEW,
    "REJECTED": VALIDATION_EVENT_TYPE_REJECTED,
}


def decode_stream_fields(
    fields: dict[str, Any],
) -> dict[str, Any]:
    decoded: dict[str, Any] = {}

    for key, value in fields.items():
        field_key = key.decode("utf-8") if isinstance(key, bytes) else str(key)

        if isinstance(value, bytes):
            decoded[field_key] = value.decode("utf-8")
        else:
            decoded[field_key] = value

    return decoded


def _normalize_event_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(
        payload,
    )

    if not normalized.get(
        "event_type",
    ) and normalized.get(
        "validation_outcome",
    ):
        normalized["event_type"] = _LEGACY_OUTCOME_TO_EVENT_TYPE.get(
            str(
                normalized[
                    "validation_outcome"
                ],
            ),
        )

    if not normalized.get(
        "version",
    ):
        normalized["version"] = VALIDATION_EVENT_VERSION

    if not normalized.get(
        "occurred_at",
    ):
        normalized["occurred_at"] = datetime.now(
            UTC,
        ).isoformat()

    return normalized


def parse_validation_event(
    fields: dict[str, Any],
) -> ValidationCompletedEvent:
    decoded_fields = decode_stream_fields(
        fields,
    )

    if "payload" in decoded_fields:
        payload = json.loads(
            decoded_fields["payload"],
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise ValueError(
                "Stream payload must be a JSON object.",
            )

        return ValidationCompletedEvent.model_validate(
            _normalize_event_payload(
                payload,
            ),
        )

    return ValidationCompletedEvent.model_validate(
        _normalize_event_payload(
            decoded_fields,
        ),
    )


def is_validation_error(
    error: Exception,
) -> bool:
    return isinstance(
        error,
        (ValueError, ValidationError),
    )
