from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, select, union, update
from sqlalchemy.orm import aliased

from src.data.models.postgres.audit_log import AuditLog
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
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
from src.data.models.postgres.users import User
from src.data.repositories.base_repo import BaseRepository

_RESOLVED_CANDIDATE_TYPES = (
    POResolutionCandidateType.RESOLVED,
    POResolutionCandidateType.RECOVERED,
)

_NEEDS_REVIEW_OUTCOMES = (
    InvoiceValidationOutcome.RECOVERED,
    InvoiceValidationOutcome.AMBIGUOUS,
    InvoiceValidationOutcome.UNRESOLVED,
    InvoiceValidationOutcome.DUPLICATE,
)


@dataclass(frozen=True, slots=True)
class InvoiceOwnershipSnapshot:
    invoice_id: UUID
    invoice_status: InvoiceStatus | None
    validation_outcome: InvoiceValidationOutcome | None
    assigned_manager_id: UUID | None


@dataclass(frozen=True, slots=True)
class InvoiceOwnershipDetailsRow:
    associate_owner_id: UUID | None
    associate_owner_name: str | None
    associate_owner_email: str | None
    assigned_manager_id: UUID | None
    assigned_manager_name: str | None
    assigned_manager_email: str | None
    escalated_by_id: UUID | None
    escalated_by_name: str | None
    escalated_by_email: str | None
    assigned_at: datetime | None


class InvoiceOwnershipRepository(BaseRepository):
    async def get_ownership_snapshot(
        self,
        invoice_id: UUID,
    ) -> InvoiceOwnershipSnapshot | None:
        result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_status,
                Invoice.validation_outcome,
                Invoice.assigned_manager_id,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return InvoiceOwnershipSnapshot(
            invoice_id=row.id,
            invoice_status=row.invoice_status,
            validation_outcome=row.validation_outcome,
            assigned_manager_id=row.assigned_manager_id,
        )

    async def is_associate_owner(
        self,
        *,
        associate_id: UUID,
        invoice_id: UUID,
    ) -> bool:
        result = await self.execute(
            select(
                1,
            ).where(
                Invoice.id == invoice_id,
                self._associate_ownership_filter(
                    associate_id,
                ),
            ),
        )

        return result.scalar_one_or_none() is not None

    async def has_associate_ownership(
        self,
        invoice_id: UUID,
    ) -> bool:
        result = await self.execute(
            select(
                1,
            ).where(
                Invoice.id == invoice_id,
                Invoice.id.in_(
                    select(
                        self._owned_invoice_ids_subquery().c.invoice_id,
                    ),
                ),
            ),
        )

        return result.scalar_one_or_none() is not None

    async def get_ownership_details(
        self,
        invoice_id: UUID,
    ) -> InvoiceOwnershipDetailsRow | None:
        result = await self.execute(
            select(
                Invoice.assigned_manager_id,
                Invoice.assigned_at,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        invoice_row = result.one_or_none()

        if invoice_row is None:
            return None

        associate_owner_id = await self.get_associate_owner_id(
            invoice_id,
        )
        escalated_by_id = await self.get_escalated_by_id(
            invoice_id,
        )

        user_ids = {
            user_id
            for user_id in (
                associate_owner_id,
                invoice_row.assigned_manager_id,
                escalated_by_id,
            )
            if user_id is not None
        }
        users_by_id = await self._get_users_by_id(
            user_ids,
        )

        associate_user = users_by_id.get(
            associate_owner_id,
        )
        manager_user = users_by_id.get(
            invoice_row.assigned_manager_id,
        )
        escalated_by_user = users_by_id.get(
            escalated_by_id,
        )

        return InvoiceOwnershipDetailsRow(
            associate_owner_id=associate_owner_id,
            associate_owner_name=(
                associate_user.name
                if associate_user is not None
                else None
            ),
            associate_owner_email=(
                associate_user.email
                if associate_user is not None
                else None
            ),
            assigned_manager_id=invoice_row.assigned_manager_id,
            assigned_manager_name=(
                manager_user.name
                if manager_user is not None
                else None
            ),
            assigned_manager_email=(
                manager_user.email
                if manager_user is not None
                else None
            ),
            escalated_by_id=escalated_by_id,
            escalated_by_name=(
                escalated_by_user.name
                if escalated_by_user is not None
                else None
            ),
            escalated_by_email=(
                escalated_by_user.email
                if escalated_by_user is not None
                else None
            ),
            assigned_at=invoice_row.assigned_at,
        )

    async def get_associate_owner_id(
        self,
        invoice_id: UUID,
    ) -> UUID | None:
        if not await self.has_associate_ownership(
            invoice_id,
        ):
            return None

        subquery = (
            InvoiceOwnershipRepository._associate_owner_ids_for_invoice_subquery(
                invoice_id,
            )
        )
        result = await self.execute(
            select(
                subquery.c.associate_owner_id,
            ).limit(
                1,
            ),
        )

        return result.scalar_one_or_none()

    async def get_escalated_by_id(
        self,
        invoice_id: UUID,
    ) -> UUID | None:
        result = await self.execute(
            select(
                AuditLog.performed_by,
            )
            .where(
                AuditLog.invoice_id == invoice_id,
                AuditLog.action == "ESCALATE",
            )
            .order_by(
                AuditLog.created_at.desc(),
            )
            .limit(
                1,
            ),
        )

        return result.scalar_one_or_none()

    async def _get_users_by_id(
        self,
        user_ids: set[UUID],
    ) -> dict[UUID, User]:
        if not user_ids:
            return {}

        result = await self.execute(
            select(
                User,
            ).where(
                User.id.in_(
                    user_ids,
                ),
            ),
        )

        return {
            user.id: user
            for user in result.scalars().all()
        }

    @staticmethod
    def _associate_owner_ids_for_invoice_subquery(
        invoice_id: UUID,
    ):
        from_mapping = (
            select(
                PurchaseOrder.uploaded_by.label(
                    "associate_owner_id",
                ),
            )
            .select_from(
                InvoicePOMapping,
            )
            .join(
                PurchaseOrder,
                InvoicePOMapping.po_id == PurchaseOrder.id,
            )
            .where(
                InvoicePOMapping.invoice_id == invoice_id,
                PurchaseOrder.uploaded_by.is_not(
                    None,
                ),
            )
        )

        from_selected_group = (
            select(
                PurchaseOrder.uploaded_by.label(
                    "associate_owner_id",
                ),
            )
            .select_from(
                InvoicePOResolutionGroup,
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
                InvoicePOResolutionGroup.invoice_id == invoice_id,
                InvoicePOResolutionGroup.is_selected.is_(
                    True,
                ),
                PurchaseOrder.uploaded_by.is_not(
                    None,
                ),
            )
        )

        single_resolved_invoice_ids = (
            select(
                InvoicePOResolutionGroup.invoice_id,
            )
            .where(
                InvoicePOResolutionGroup.invoice_id == invoice_id,
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
                PurchaseOrder.uploaded_by.label(
                    "associate_owner_id",
                ),
            )
            .select_from(
                resolution_group,
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
                resolution_group.invoice_id == invoice_id,
                resolution_group.candidate_type.in_(
                    _RESOLVED_CANDIDATE_TYPES,
                ),
                resolution_group.invoice_id.in_(
                    single_resolved_invoice_ids,
                ),
                PurchaseOrder.uploaded_by.is_not(
                    None,
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

    async def assign_manager(
        self,
        *,
        invoice_id: UUID,
        manager_id: UUID,
    ) -> None:
        await self.execute(
            update(Invoice)
            .where(
                Invoice.id == invoice_id,
            )
            .values(
                assigned_manager_id=manager_id,
                assigned_at=func.now(),
            ),
        )

    @staticmethod
    def associate_ownership_filter(
        associate_id: UUID,
    ) -> ColumnElement[bool]:
        return Invoice.id.in_(
            select(
                InvoiceOwnershipRepository._owned_invoice_ids_subquery(
                    associate_id,
                ).c.invoice_id,
            ),
        )

    @staticmethod
    def _associate_ownership_filter(
        associate_id: UUID,
    ) -> ColumnElement[bool]:
        return InvoiceOwnershipRepository.associate_ownership_filter(
            associate_id,
        )

    @staticmethod
    def unassigned_queue_filter() -> ColumnElement[bool]:
        return (
            (Invoice.invoice_status == InvoiceStatus.UNDER_REVIEW)
            & (
                Invoice.validation_outcome.in_(
                    _NEEDS_REVIEW_OUTCOMES,
                )
            )
            & (Invoice.assigned_manager_id.is_(None))
            & (
                ~Invoice.id.in_(
                    select(
                        InvoiceOwnershipRepository._owned_invoice_ids_subquery().c.invoice_id,
                    ),
                )
            )
        )

    @staticmethod
    def manager_assigned_filter(
        manager_id: UUID,
    ) -> ColumnElement[bool]:
        return Invoice.assigned_manager_id == manager_id

    @staticmethod
    def _owned_invoice_ids_subquery(
        associate_id: UUID | None = None,
    ):
        if associate_id is not None:
            po_filter = PurchaseOrder.uploaded_by == associate_id
        else:
            po_filter = PurchaseOrder.uploaded_by.is_not(None)

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
                po_filter,
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
                po_filter,
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
                po_filter,
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
