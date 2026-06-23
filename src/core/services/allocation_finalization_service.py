from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.approval_exc import (
    InvoiceApprovalValidationError,
)
from src.core.workflow.po_status_calculator import (
    POStatusCalculator,
)
from src.data.repositories.approval_repo import (
    ApprovalRepository,
    SelectedAllocationCandidateItem,
)


class AllocationFinalizationService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.approval_repo = ApprovalRepository(
            session,
        )
        self.po_status_calculator = POStatusCalculator()

    async def finalize_allocations(
        self,
        items: list[SelectedAllocationCandidateItem],
    ) -> set[UUID]:
        consumed_amount_by_po: dict[
            UUID,
            Decimal,
        ] = defaultdict(
            Decimal,
        )

        for item in items:
            po_line_item = (
                await self.approval_repo.increment_po_line_consumption(
                    item.po_line_item_id,
                    item.allocated_quantity,
                )
            )

            if po_line_item is None:
                raise InvoiceApprovalValidationError(
                    "Allocation references invalid PO line item.",
                )

            consumed_amount_by_po[
                item.po_id
            ] += item.allocated_amount

        affected_po_ids = set(
            consumed_amount_by_po.keys(),
        )

        for po_id, amount in consumed_amount_by_po.items():
            purchase_order = (
                await self.approval_repo.increment_po_consumed_amount(
                    po_id,
                    amount,
                )
            )

            if purchase_order is None:
                raise InvoiceApprovalValidationError(
                    "PO not found for finalized allocation.",
                )

        for po_id in affected_po_ids:
            await self._recalculate_po_status(
                po_id,
            )

        return affected_po_ids

    async def _recalculate_po_status(
        self,
        po_id: UUID,
    ) -> None:
        po_line_items = (
            await self.approval_repo.get_po_line_items_for_update(
                po_id,
            )
        )

        if not po_line_items:
            raise InvoiceApprovalValidationError(
                "PO line items not found for status recalculation.",
            )

        snapshots = [
            self.po_status_calculator.snapshot_from_po_line(
                po_line_item,
            )
            for po_line_item in po_line_items
        ]
        new_status = self.po_status_calculator.calculate_status(
            snapshots,
        )

        await self.approval_repo.update_po_status(
            po_id,
            new_status,
        )

    async def create_final_records(
        self,
        *,
        invoice_id: UUID,
        po_ids: list[UUID],
        allocation_items: list[SelectedAllocationCandidateItem],
    ) -> None:
        for po_id in po_ids:
            exists = await self.approval_repo.purchase_order_exists(
                po_id,
            )

            if not exists:
                raise InvoiceApprovalValidationError(
                    "PO not found for selected candidate mapping.",
                )

        await self.approval_repo.create_po_mappings(
            invoice_id,
            po_ids,
        )
        await self.approval_repo.create_final_allocations(
            allocation_items,
        )
