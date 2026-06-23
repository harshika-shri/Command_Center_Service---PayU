from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.invoice_po_resolution_groups import (
    InvoicePOResolutionGroup,
    InvoicePOResolutionGroupItem,
)
from src.data.models.postgres.purchase_orders import PurchaseOrder
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class POCandidateGroupRow:
    id: UUID
    candidate_type: str
    confidence_score: Decimal | None
    is_selected: bool


@dataclass(frozen=True, slots=True)
class POCandidatePurchaseOrderRow:
    resolution_group_id: UUID
    po_id: UUID
    po_number: str
    status: str
    total_amount: Decimal | None
    consumed_amount: Decimal
    po_date: date
    vendor_name: str | None


@dataclass(frozen=True, slots=True)
class POCandidateData:
    groups: list[POCandidateGroupRow]
    purchase_orders: list[POCandidatePurchaseOrderRow]


class POCandidateRepository(BaseRepository):
    async def get_po_candidates(
        self,
        invoice_id: UUID,
    ) -> POCandidateData:
        groups_result = await self.execute(
            select(
                InvoicePOResolutionGroup.id,
                InvoicePOResolutionGroup.candidate_type,
                InvoicePOResolutionGroup.confidence_score,
                InvoicePOResolutionGroup.is_selected,
            )
            .where(
                InvoicePOResolutionGroup.invoice_id == invoice_id,
            )
            .order_by(
                InvoicePOResolutionGroup.created_at.asc(),
            ),
        )

        groups = [
            POCandidateGroupRow(
                id=row.id,
                candidate_type=row.candidate_type.value,
                confidence_score=row.confidence_score,
                is_selected=row.is_selected,
            )
            for row in groups_result.all()
        ]

        if not groups:
            return POCandidateData(
                groups=[],
                purchase_orders=[],
            )

        purchase_orders_result = await self.execute(
            select(
                InvoicePOResolutionGroupItem.resolution_group_id,
                PurchaseOrder.id,
                PurchaseOrder.po_number,
                PurchaseOrder.status,
                PurchaseOrder.total_amount,
                PurchaseOrder.consumed_amount,
                PurchaseOrder.po_date,
                VendorMaster.vendor_name,
            )
            .select_from(
                InvoicePOResolutionGroupItem,
            )
            .join(
                InvoicePOResolutionGroup,
                InvoicePOResolutionGroupItem.resolution_group_id
                == InvoicePOResolutionGroup.id,
            )
            .join(
                PurchaseOrder,
                InvoicePOResolutionGroupItem.po_id == PurchaseOrder.id,
            )
            .outerjoin(
                VendorMaster,
                PurchaseOrder.vendor_id == VendorMaster.id,
            )
            .where(
                InvoicePOResolutionGroup.invoice_id == invoice_id,
            ),
        )

        purchase_orders = [
            POCandidatePurchaseOrderRow(
                resolution_group_id=row.resolution_group_id,
                po_id=row.id,
                po_number=row.po_number,
                status=row.status.value,
                total_amount=row.total_amount,
                consumed_amount=row.consumed_amount,
                po_date=row.po_date,
                vendor_name=row.vendor_name,
            )
            for row in purchase_orders_result.all()
        ]

        return POCandidateData(
            groups=groups,
            purchase_orders=purchase_orders,
        )
