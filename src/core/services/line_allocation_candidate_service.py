from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.invoice_access_service import (
    InvoiceAccessService,
)
from src.data.repositories.line_allocation_candidate_repo import (
    LineAllocationCandidateData,
    LineAllocationCandidateRepository,
)
from src.schemas.invoice_review_schema import (
    LineAllocationCandidateGroupDetails,
    LineAllocationCandidateItemDetails,
    LineAllocationCandidateResponse,
    LineAllocationInvoiceLineDetails,
    LineAllocationPOLineDetails,
)
from src.utils.decimal_utils import decimal_to_float


class LineAllocationCandidateService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.access_service = InvoiceAccessService(
            session,
        )
        self.line_allocation_repo = LineAllocationCandidateRepository(
            session,
        )

    async def get_line_allocation_candidates(
        self,
        invoice_id: UUID,
        *,
        require_exists: bool = True,
    ) -> LineAllocationCandidateResponse:
        if require_exists:
            await self.access_service.ensure_invoice_exists(
                invoice_id,
            )

        data = await self.line_allocation_repo.get_line_allocation_candidates(
            invoice_id,
        )

        return self._map_line_allocation_candidates(
            data,
        )

    @staticmethod
    def _map_line_allocation_candidates(
        data: LineAllocationCandidateData,
    ) -> LineAllocationCandidateResponse:
        items_by_group: dict[
            UUID,
            list[LineAllocationCandidateItemDetails],
        ] = defaultdict(
            list,
        )

        for item in data.items:
            items_by_group[item.allocation_candidate_group_id].append(
                LineAllocationCandidateItemDetails(
                    id=item.id,
                    invoice_line_item_id=item.invoice_line_item_id,
                    po_line_item_id=item.po_line_item_id,
                    allocated_quantity=decimal_to_float(
                        item.allocated_quantity,
                    )
                    or 0.0,
                    allocated_amount=decimal_to_float(
                        item.allocated_amount,
                    )
                    or 0.0,
                    candidate_type=item.candidate_type,
                    invoice_line_item=LineAllocationInvoiceLineDetails(
                        item_code=item.invoice_item_code,
                        item_description=item.invoice_item_description,
                        quantity_billed=decimal_to_float(
                            item.invoice_quantity_billed,
                        )
                        or 0.0,
                        line_total=decimal_to_float(
                            item.invoice_line_total,
                        )
                        or 0.0,
                    ),
                    po_line_item=LineAllocationPOLineDetails(
                        item_code=item.po_item_code,
                        item_description=item.po_item_description,
                        quantity_ordered=decimal_to_float(
                            item.po_quantity_ordered,
                        )
                        or 0.0,
                        consumed_quantity=decimal_to_float(
                            item.po_consumed_quantity,
                        )
                        or 0.0,
                        line_total=decimal_to_float(
                            item.po_line_total,
                        )
                        or 0.0,
                    ),
                ),
            )

        return LineAllocationCandidateResponse(
            candidate_groups=[
                LineAllocationCandidateGroupDetails(
                    id=group.id,
                    candidate_type=group.candidate_type,
                    confidence_score=decimal_to_float(
                        group.confidence_score,
                    ),
                    is_selected=group.is_selected,
                    items=items_by_group.get(
                        group.id,
                        [],
                    ),
                )
                for group in data.groups
            ],
        )
