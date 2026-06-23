from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.invoice_access_service import (
    InvoiceAccessService,
)
from src.data.repositories.po_candidate_repo import (
    POCandidateData,
    POCandidateRepository,
)
from src.schemas.invoice_review_schema import (
    POCandidateGroupDetails,
    POCandidatePurchaseOrderDetails,
    POCandidateResponse,
)
from src.utils.decimal_utils import decimal_to_float


class POCandidateService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.access_service = InvoiceAccessService(
            session,
        )
        self.po_candidate_repo = POCandidateRepository(
            session,
        )

    async def get_po_candidates(
        self,
        invoice_id: UUID,
        *,
        require_exists: bool = True,
    ) -> POCandidateResponse:
        if require_exists:
            await self.access_service.ensure_invoice_exists(
                invoice_id,
            )

        data = await self.po_candidate_repo.get_po_candidates(
            invoice_id,
        )

        return self._map_po_candidates(
            data,
        )

    @staticmethod
    def _map_po_candidates(
        data: POCandidateData,
    ) -> POCandidateResponse:
        purchase_orders_by_group: dict[
            UUID,
            list[POCandidatePurchaseOrderDetails],
        ] = defaultdict(
            list,
        )

        for purchase_order in data.purchase_orders:
            purchase_orders_by_group[purchase_order.resolution_group_id].append(
                POCandidatePurchaseOrderDetails(
                    po_id=purchase_order.po_id,
                    po_number=purchase_order.po_number,
                    status=purchase_order.status,
                    total_amount=decimal_to_float(
                        purchase_order.total_amount,
                    ),
                    consumed_amount=decimal_to_float(
                        purchase_order.consumed_amount,
                    )
                    or 0.0,
                    po_date=purchase_order.po_date,
                    vendor_name=purchase_order.vendor_name,
                ),
            )

        return POCandidateResponse(
            candidate_groups=[
                POCandidateGroupDetails(
                    id=group.id,
                    candidate_type=group.candidate_type,
                    confidence_score=decimal_to_float(
                        group.confidence_score,
                    ),
                    is_selected=group.is_selected,
                    purchase_orders=purchase_orders_by_group.get(
                        group.id,
                        [],
                    ),
                )
                for group in data.groups
            ],
        )
