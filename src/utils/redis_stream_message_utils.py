from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.constants.redis_stream_constants import (
    VALIDATION_EVENT_TYPE_AMBIGUOUS,
    VALIDATION_EVENT_TYPE_DUPLICATE,
    VALIDATION_EVENT_TYPE_RECOVERED,
    VALIDATION_EVENT_TYPE_RESOLVED,
    VALIDATION_EVENT_TYPE_UNRESOLVED,
)
from src.schemas.validation_event_schema import (
    ValidationCompletedEvent,
)

_LEGACY_EVENT_TYPE_TO_OUTCOME = {
    "validation.completed": "resolved",
    "validation.pending_review": "recovered",
    "validation.rejected": "unresolved",
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
            payload,
        )

    if "validation_outcome" not in decoded_fields:
        legacy_outcome = _LEGACY_EVENT_TYPE_TO_OUTCOME.get(
            str(
                decoded_fields.get(
                    "event_type",
                    "",
                ),
            ),
        )

        if legacy_outcome is not None:
            decoded_fields = {
                **decoded_fields,
                "validation_outcome": legacy_outcome,
            }
        elif decoded_fields.get("event_type") in {
            VALIDATION_EVENT_TYPE_RESOLVED,
            VALIDATION_EVENT_TYPE_RECOVERED,
            VALIDATION_EVENT_TYPE_AMBIGUOUS,
            VALIDATION_EVENT_TYPE_UNRESOLVED,
            VALIDATION_EVENT_TYPE_DUPLICATE,
        }:
            event_type = str(
                decoded_fields["event_type"],
            )
            decoded_fields = {
                **decoded_fields,
                "validation_outcome": event_type.removeprefix(
                    "validation.",
                ),
            }

    return ValidationCompletedEvent.model_validate(
        decoded_fields,
    )


def is_validation_error(
    error: Exception,
) -> bool:
    return isinstance(
        error,
        (ValueError, ValidationError),
    )
