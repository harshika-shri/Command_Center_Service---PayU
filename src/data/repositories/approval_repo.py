from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update

from src.data.models.postgres.enums import (
    AllocationStatus,
    InvoiceStatus,
    InvoiceValidationOutcome,
    PurchaseOrderStatus,
)
from src.data.models.postgres.invoice_line_allocation_candidates import (
    InvoiceLineAllocationCandidateGroup,
    InvoiceLineAllocationCandidateItem,
)
from src.data.models.postgres.invoice_line_items import InvoiceLineItem
from src.data.models.postgres.invoice_line_po_allocations import (
    InvoiceLinePOAllocation,
)
from src.data.models.postgres.invoice_po_mapping import InvoicePOMapping
from src.data.models.postgres.invoice_po_resolution_groups import (
    InvoicePOResolutionGroup,
    InvoicePOResolutionGroupItem,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.po_line_items import POLineItem
from src.data.models.postgres.purchase_orders import PurchaseOrder
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class InvoiceApprovalSnapshot:
    invoice_id: UUID
    invoice_status: InvoiceStatus | None
    validation_outcome: InvoiceValidationOutcome | None


@dataclass(frozen=True, slots=True)
class SelectedPOCandidate:
    group_id: UUID
    po_ids: list[UUID]


@dataclass(frozen=True, slots=True)
class SelectedAllocationCandidateItem:
    invoice_line_item_id: UUID
    po_line_item_id: UUID
    po_id: UUID
    allocated_quantity: Decimal
    allocated_amount: Decimal


@dataclass(frozen=True, slots=True)
class SelectedAllocationCandidate:
    group_id: UUID
    items: list[SelectedAllocationCandidateItem]


class ApprovalRepository(BaseRepository):
    async def get_invoice_for_update(
        self,
        invoice_id: UUID,
    ) -> InvoiceApprovalSnapshot | None:
        result = await self.execute(
            select(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .with_for_update(),
        )
        invoice = result.scalar_one_or_none()

        if invoice is None:
            return None

        return InvoiceApprovalSnapshot(
            invoice_id=invoice.id,
            invoice_status=invoice.invoice_status,
            validation_outcome=invoice.validation_outcome,
        )

    async def get_selected_po_candidate(
        self,
        invoice_id: UUID,
    ) -> SelectedPOCandidate | None:
        groups_result = await self.execute(
            select(
                InvoicePOResolutionGroup.id,
            )
            .where(
                InvoicePOResolutionGroup.invoice_id == invoice_id,
                InvoicePOResolutionGroup.is_selected.is_(True),
            ),
        )
        group_ids = list(
            groups_result.scalars().all(),
        )

        if len(group_ids) != 1:
            return None

        group_id = group_ids[0]
        items_result = await self.execute(
            select(
                InvoicePOResolutionGroupItem.po_id,
            ).where(
                InvoicePOResolutionGroupItem.resolution_group_id
                == group_id,
            ),
        )

        return SelectedPOCandidate(
            group_id=group_id,
            po_ids=list(
                items_result.scalars().all(),
            ),
        )

    async def get_selected_allocation_candidate(
        self,
        invoice_id: UUID,
    ) -> SelectedAllocationCandidate | None:
        groups_result = await self.execute(
            select(
                InvoiceLineAllocationCandidateGroup.id,
            )
            .where(
                InvoiceLineAllocationCandidateGroup.invoice_id
                == invoice_id,
                InvoiceLineAllocationCandidateGroup.is_selected.is_(
                    True,
                ),
            ),
        )
        group_ids = list(
            groups_result.scalars().all(),
        )

        if len(group_ids) != 1:
            return None

        group_id = group_ids[0]
        items_result = await self.execute(
            select(
                InvoiceLineAllocationCandidateItem.invoice_line_item_id,
                InvoiceLineAllocationCandidateItem.po_line_item_id,
                InvoiceLineAllocationCandidateItem.allocated_quantity,
                InvoiceLineAllocationCandidateItem.allocated_amount,
                POLineItem.po_id,
            )
            .join(
                POLineItem,
                InvoiceLineAllocationCandidateItem.po_line_item_id
                == POLineItem.id,
            )
            .join(
                InvoiceLineItem,
                InvoiceLineAllocationCandidateItem.invoice_line_item_id
                == InvoiceLineItem.id,
            )
            .where(
                InvoiceLineAllocationCandidateItem.allocation_candidate_group_id
                == group_id,
                InvoiceLineItem.invoice_id == invoice_id,
            ),
        )

        items = [
            SelectedAllocationCandidateItem(
                invoice_line_item_id=row.invoice_line_item_id,
                po_line_item_id=row.po_line_item_id,
                po_id=row.po_id,
                allocated_quantity=row.allocated_quantity,
                allocated_amount=row.allocated_amount,
            )
            for row in items_result.all()
        ]

        if not items:
            return None

        return SelectedAllocationCandidate(
            group_id=group_id,
            items=items,
        )

    async def purchase_order_exists(
        self,
        po_id: UUID,
    ) -> bool:
        result = await self.execute(
            select(
                PurchaseOrder.id,
            ).where(
                PurchaseOrder.id == po_id,
            ),
        )

        return result.scalar_one_or_none() is not None

    async def create_po_mappings(
        self,
        invoice_id: UUID,
        po_ids: list[UUID],
    ) -> None:
        unique_po_ids = list(
            dict.fromkeys(
                po_ids,
            ),
        )

        for po_id in unique_po_ids:
            self.session.add(
                InvoicePOMapping(
                    invoice_id=invoice_id,
                    po_id=po_id,
                ),
            )

        if unique_po_ids:
            await self.session.flush()

    async def create_final_allocations(
        self,
        items: list[SelectedAllocationCandidateItem],
    ) -> None:
        for item in items:
            self.session.add(
                InvoiceLinePOAllocation(
                    invoice_line_item_id=item.invoice_line_item_id,
                    po_id=item.po_id,
                    po_line_item_id=item.po_line_item_id,
                    allocated_quantity=item.allocated_quantity,
                    allocated_amount=item.allocated_amount,
                    match_type=None,
                    match_confidence=None,
                    is_confirmed=True,
                    allocation_status=AllocationStatus.CONFIRMED.value,
                ),
            )

        if items:
            await self.session.flush()

    async def increment_po_line_consumption(
        self,
        po_line_item_id: UUID,
        allocated_quantity: Decimal,
    ) -> POLineItem | None:
        result = await self.execute(
            select(POLineItem)
            .where(
                POLineItem.id == po_line_item_id,
            )
            .with_for_update(),
        )
        po_line_item = result.scalar_one_or_none()

        if po_line_item is None:
            return None

        po_line_item.consumed_quantity = (
            po_line_item.consumed_quantity
            + allocated_quantity
        )
        await self.session.flush()

        return po_line_item

    async def increment_po_consumed_amount(
        self,
        po_id: UUID,
        allocated_amount: Decimal,
    ) -> PurchaseOrder | None:
        result = await self.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.id == po_id,
            )
            .with_for_update(),
        )
        purchase_order = result.scalar_one_or_none()

        if purchase_order is None:
            return None

        purchase_order.consumed_amount = (
            purchase_order.consumed_amount
            + allocated_amount
        )
        await self.session.flush()

        return purchase_order

    async def get_po_line_items_for_update(
        self,
        po_id: UUID,
    ) -> list[POLineItem]:
        result = await self.execute(
            select(POLineItem)
            .where(
                POLineItem.po_id == po_id,
            )
            .with_for_update(),
        )

        return list(
            result.scalars().all(),
        )

    async def update_po_status(
        self,
        po_id: UUID,
        status: PurchaseOrderStatus,
    ) -> None:
        await self.execute(
            update(PurchaseOrder)
            .where(
                PurchaseOrder.id == po_id,
            )
            .values(
                status=status,
            ),
        )

    async def mark_invoice_ready_to_pay(
        self,
        invoice_id: UUID,
    ) -> None:
        await self.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .values(
                invoice_status=InvoiceStatus.READY_TO_PAY,
                paid_at=None,
                paid_by=None,
            ),
        )
