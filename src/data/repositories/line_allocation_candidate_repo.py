from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.invoice_line_allocation_candidates import (
    InvoiceLineAllocationCandidateGroup,
    InvoiceLineAllocationCandidateItem,
)
from src.data.models.postgres.invoice_line_items import InvoiceLineItem
from src.data.models.postgres.po_line_items import POLineItem
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class LineAllocationGroupRow:
    id: UUID
    candidate_type: str
    confidence_score: Decimal | None
    is_selected: bool


@dataclass(frozen=True, slots=True)
class LineAllocationItemRow:
    id: UUID
    allocation_candidate_group_id: UUID
    invoice_line_item_id: UUID
    po_line_item_id: UUID
    allocated_quantity: Decimal
    allocated_amount: Decimal
    candidate_type: str
    invoice_item_code: str | None
    invoice_item_description: str | None
    invoice_quantity_billed: Decimal
    invoice_line_total: Decimal
    po_item_code: str | None
    po_item_description: str
    po_quantity_ordered: Decimal
    po_consumed_quantity: Decimal
    po_line_total: Decimal


@dataclass(frozen=True, slots=True)
class LineAllocationCandidateData:
    groups: list[LineAllocationGroupRow]
    items: list[LineAllocationItemRow]


class LineAllocationCandidateRepository(BaseRepository):
    async def get_line_allocation_candidates(
        self,
        invoice_id: UUID,
    ) -> LineAllocationCandidateData:
        groups_result = await self.execute(
            select(
                InvoiceLineAllocationCandidateGroup.id,
                InvoiceLineAllocationCandidateGroup.candidate_type,
                InvoiceLineAllocationCandidateGroup.confidence_score,
                InvoiceLineAllocationCandidateGroup.is_selected,
            )
            .where(
                InvoiceLineAllocationCandidateGroup.invoice_id == invoice_id,
            )
            .order_by(
                InvoiceLineAllocationCandidateGroup.created_at.asc(),
            ),
        )

        groups = [
            LineAllocationGroupRow(
                id=row.id,
                candidate_type=row.candidate_type.value,
                confidence_score=row.confidence_score,
                is_selected=row.is_selected,
            )
            for row in groups_result.all()
        ]

        if not groups:
            return LineAllocationCandidateData(
                groups=[],
                items=[],
            )

        items_result = await self.execute(
            select(
                InvoiceLineAllocationCandidateItem.id,
                InvoiceLineAllocationCandidateItem.allocation_candidate_group_id,
                InvoiceLineAllocationCandidateItem.invoice_line_item_id,
                InvoiceLineAllocationCandidateItem.po_line_item_id,
                InvoiceLineAllocationCandidateItem.allocated_quantity,
                InvoiceLineAllocationCandidateItem.allocated_amount,
                InvoiceLineAllocationCandidateItem.candidate_type,
                InvoiceLineItem.item_code.label(
                    "invoice_item_code",
                ),
                InvoiceLineItem.item_description.label(
                    "invoice_item_description",
                ),
                InvoiceLineItem.quantity_billed.label(
                    "invoice_quantity_billed",
                ),
                InvoiceLineItem.line_total.label(
                    "invoice_line_total",
                ),
                POLineItem.item_code.label(
                    "po_item_code",
                ),
                POLineItem.item_description.label(
                    "po_item_description",
                ),
                POLineItem.quantity_ordered.label(
                    "po_quantity_ordered",
                ),
                POLineItem.consumed_quantity.label(
                    "po_consumed_quantity",
                ),
                POLineItem.line_total.label(
                    "po_line_total",
                ),
            )
            .select_from(
                InvoiceLineAllocationCandidateItem,
            )
            .join(
                InvoiceLineAllocationCandidateGroup,
                InvoiceLineAllocationCandidateItem.allocation_candidate_group_id
                == InvoiceLineAllocationCandidateGroup.id,
            )
            .join(
                InvoiceLineItem,
                InvoiceLineAllocationCandidateItem.invoice_line_item_id
                == InvoiceLineItem.id,
            )
            .join(
                POLineItem,
                InvoiceLineAllocationCandidateItem.po_line_item_id == POLineItem.id,
            )
            .where(
                InvoiceLineAllocationCandidateGroup.invoice_id == invoice_id,
            )
            .order_by(
                InvoiceLineAllocationCandidateItem.created_at.asc(),
            ),
        )

        items = [
            LineAllocationItemRow(
                id=row.id,
                allocation_candidate_group_id=row.allocation_candidate_group_id,
                invoice_line_item_id=row.invoice_line_item_id,
                po_line_item_id=row.po_line_item_id,
                allocated_quantity=row.allocated_quantity,
                allocated_amount=row.allocated_amount,
                candidate_type=row.candidate_type.value,
                invoice_item_code=row.invoice_item_code,
                invoice_item_description=row.invoice_item_description,
                invoice_quantity_billed=row.invoice_quantity_billed,
                invoice_line_total=row.invoice_line_total,
                po_item_code=row.po_item_code,
                po_item_description=row.po_item_description,
                po_quantity_ordered=row.po_quantity_ordered,
                po_consumed_quantity=row.po_consumed_quantity,
                po_line_total=row.po_line_total,
            )
            for row in items_result.all()
        ]

        return LineAllocationCandidateData(
            groups=groups,
            items=items,
        )
