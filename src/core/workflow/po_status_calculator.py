from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.data.models.postgres.enums import (
    PurchaseOrderStatus,
)
from src.data.models.postgres.po_line_items import POLineItem


@dataclass(frozen=True, slots=True)
class POLineItemConsumptionSnapshot:
    quantity_ordered: Decimal
    consumed_quantity: Decimal


class POStatusCalculator:
    @staticmethod
    def calculate_status(
        line_items: list[POLineItemConsumptionSnapshot],
    ) -> PurchaseOrderStatus:
        if not line_items:
            return PurchaseOrderStatus.OPEN

        if all(
            line_item.consumed_quantity <= 0
            for line_item in line_items
        ):
            return PurchaseOrderStatus.OPEN

        if all(
            line_item.consumed_quantity
            >= line_item.quantity_ordered
            for line_item in line_items
        ):
            return PurchaseOrderStatus.CLOSED

        return PurchaseOrderStatus.PARTIALLY_PROCESSED

    @staticmethod
    def snapshot_from_po_line(
        po_line_item: POLineItem,
    ) -> POLineItemConsumptionSnapshot:
        return POLineItemConsumptionSnapshot(
            quantity_ordered=po_line_item.quantity_ordered,
            consumed_quantity=po_line_item.consumed_quantity,
        )
