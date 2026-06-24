from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select, union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.core.exceptions.access_exc import (
    InvoiceAccessDeniedError,
)
from src.data.models.postgres.enums import (
    POResolutionCandidateType,
)
from src.data.models.postgres.invoice_po_mapping import (
    InvoicePOMapping,
)
from src.data.models.postgres.invoice_po_resolution_groups import (
    InvoicePOResolutionGroup,
    InvoicePOResolutionGroupItem,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.purchase_orders import PurchaseOrder

_RESOLVED_CANDIDATE_TYPES = (
    POResolutionCandidateType.RESOLVED,
    POResolutionCandidateType.RECOVERED,
)


class OwnershipResolverService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def is_invoice_owned_by(
        self,
        invoice_id: UUID,
        associate_id: UUID,
    ) -> bool:
        result = await self.session.execute(
            select(
                1,
            ).where(
                Invoice.id == invoice_id,
                self._invoice_owned_by_filter(
                    associate_id,
                ),
            ),
        )

        return result.scalar_one_or_none() is not None

    async def ensure_invoice_owned_by(
        self,
        invoice_id: UUID,
        associate_id: UUID,
    ) -> None:
        if not await self.is_invoice_owned_by(
            invoice_id,
            associate_id,
        ):
            raise InvoiceAccessDeniedError()

    @staticmethod
    def _invoice_owned_by_filter(
        associate_id: UUID,
    ) -> ColumnElement[bool]:
        owned_invoice_ids = (
            OwnershipResolverService._owned_invoice_ids_subquery(
                associate_id,
            )
        )

        return Invoice.id.in_(
            select(
                owned_invoice_ids.c.invoice_id,
            ),
        )

    @staticmethod
    def _owned_invoice_ids_subquery(
        associate_id: UUID,
    ):
        po_owned_by_associate = (
            PurchaseOrder.uploaded_by == associate_id
        )

        from_mapping = (
            select(
                InvoicePOMapping.invoice_id.label(
                    "invoice_id",
                ),
            )
            .join(
                PurchaseOrder,
                InvoicePOMapping.po_id == PurchaseOrder.id,
            )
            .where(
                po_owned_by_associate,
            )
        )

        from_selected_group = (
            select(
                InvoicePOResolutionGroup.invoice_id.label(
                    "invoice_id",
                ),
            )
            .join(
                InvoicePOResolutionGroupItem,
                InvoicePOResolutionGroupItem.resolution_group_id
                == InvoicePOResolutionGroup.id,
            )
            .join(
                PurchaseOrder,
                InvoicePOResolutionGroupItem.po_id == PurchaseOrder.id,
            )
            .where(
                po_owned_by_associate,
                InvoicePOResolutionGroup.is_selected.is_(
                    True,
                ),
            )
        )

        single_resolved_invoice_ids = (
            select(
                InvoicePOResolutionGroup.invoice_id,
            )
            .where(
                InvoicePOResolutionGroup.candidate_type.in_(
                    _RESOLVED_CANDIDATE_TYPES,
                ),
            )
            .group_by(
                InvoicePOResolutionGroup.invoice_id,
            )
            .having(
                func.count(
                    InvoicePOResolutionGroup.id,
                )
                == 1,
            )
        )

        resolution_group = aliased(
            InvoicePOResolutionGroup,
        )
        from_single_resolved_group = (
            select(
                resolution_group.invoice_id.label(
                    "invoice_id",
                ),
            )
            .join(
                InvoicePOResolutionGroupItem,
                InvoicePOResolutionGroupItem.resolution_group_id
                == resolution_group.id,
            )
            .join(
                PurchaseOrder,
                InvoicePOResolutionGroupItem.po_id == PurchaseOrder.id,
            )
            .where(
                po_owned_by_associate,
                resolution_group.candidate_type.in_(
                    _RESOLVED_CANDIDATE_TYPES,
                ),
                resolution_group.invoice_id.in_(
                    single_resolved_invoice_ids,
                ),
                ~exists(
                    select(
                        1,
                    )
                    .select_from(
                        InvoicePOResolutionGroup,
                    )
                    .where(
                        InvoicePOResolutionGroup.invoice_id
                        == resolution_group.invoice_id,
                        InvoicePOResolutionGroup.is_selected.is_(
                            True,
                        ),
                    ),
                ),
            )
        )

        return union(
            from_mapping,
            from_selected_group,
            from_single_resolved_group,
        ).subquery()
