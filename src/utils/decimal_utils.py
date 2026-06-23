from __future__ import annotations

from decimal import Decimal
from typing import TypeVar

T = TypeVar("T")


def decimal_to_float(
    value: Decimal | float | int | None,
) -> float | None:
    if value is None:
        return None

    return float(
        value,
    )
