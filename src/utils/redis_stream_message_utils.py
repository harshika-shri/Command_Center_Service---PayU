from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.schemas.validation_event_schema import (
    ValidationCompletedEvent,
)


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
