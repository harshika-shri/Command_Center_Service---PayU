from __future__ import annotations

import json
from datetime import UTC, datetime
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
    VALIDATION_EVENT_VERSION,
    ValidationCompletedEvent,
)

_LEGACY_EVENT_TYPE_TO_OUTCOME = {
    "validation.completed": "resolved",
    "validation.pending_review": "recovered",
    "validation.rejected": "unresolved",
}

_LEGACY_OUTCOME_VALUES = {
    "approved": "resolved",
    "pending_review": "recovered",
    "rejected": "unresolved",
}

_NEW_EVENT_TYPES = frozenset(
    {
        VALIDATION_EVENT_TYPE_RESOLVED,
        VALIDATION_EVENT_TYPE_RECOVERED,
        VALIDATION_EVENT_TYPE_AMBIGUOUS,
        VALIDATION_EVENT_TYPE_UNRESOLVED,
        VALIDATION_EVENT_TYPE_DUPLICATE,
    },
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


def _event_type_to_outcome(
    event_type: str,
) -> str | None:
    if event_type in _LEGACY_EVENT_TYPE_TO_OUTCOME:
        return _LEGACY_EVENT_TYPE_TO_OUTCOME[event_type]

    if event_type in _NEW_EVENT_TYPES:
        return event_type.removeprefix(
            "validation.",
        )

    return None


def _ensure_validation_outcome(
    fields: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(
        fields,
    )

    if normalized.get(
        "validation_outcome",
    ):
        outcome = str(
            normalized["validation_outcome"],
        ).lower()
        normalized["validation_outcome"] = _LEGACY_OUTCOME_VALUES.get(
            outcome,
            outcome,
        )
        return normalized

    event_type = str(
        normalized.get(
            "event_type",
            "",
        ),
    )
    derived_outcome = _event_type_to_outcome(
        event_type,
    )

    if derived_outcome is not None:
        normalized["validation_outcome"] = derived_outcome

    return normalized


def _normalize_event_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = _ensure_validation_outcome(
        payload,
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
