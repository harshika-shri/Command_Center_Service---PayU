from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from uuid import UUID

_pending_events: ContextVar[list[PendingSSEEvent] | None] = ContextVar(
    "sse_pending_events",
    default=None,
)


@dataclass(frozen=True, slots=True)
class PendingSSEEvent:
    event_type: str
    payload: dict[str, object]
    recipient_user_ids: frozenset[UUID] = field(
        default_factory=frozenset,
    )


def append_pending_event(
    event: PendingSSEEvent,
) -> None:
    pending = _pending_events.get()

    if pending is None:
        pending = []
        _pending_events.set(
            pending,
        )

    pending.append(
        event,
    )


def drain_pending_events() -> list[PendingSSEEvent]:
    pending = _pending_events.get()

    if not pending:
        return []

    _pending_events.set(
        [],
    )

    return pending


def clear_pending_events() -> None:
    _pending_events.set(
        [],
    )
