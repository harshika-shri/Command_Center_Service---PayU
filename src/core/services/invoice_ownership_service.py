from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.access_exc import (
    InvoiceAccessDeniedError,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
    UserRole,
)
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)


class InvoiceOwnershipService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.ownership_repo = InvoiceOwnershipRepository(
            session,
        )

    async def is_associate_owner(
        self,
        *,
        associate_id: UUID,
        invoice_id: UUID,
    ) -> bool:
        return await self.ownership_repo.is_associate_owner(
            associate_id=associate_id,
            invoice_id=invoice_id,
        )

    async def is_manager_owner(
        self,
        *,
        manager_id: UUID,
        invoice_id: UUID,
    ) -> bool:
        snapshot = await self.ownership_repo.get_ownership_snapshot(
            invoice_id,
        )

        if snapshot is None:
            return False

        return snapshot.assigned_manager_id == manager_id

    async def is_unassigned(
        self,
        invoice_id: UUID,
    ) -> bool:
        snapshot = await self.ownership_repo.get_ownership_snapshot(
            invoice_id,
        )

        if snapshot is None:
            return False

        if snapshot.assigned_manager_id is not None:
            return False

        return not await self.ownership_repo.has_associate_ownership(
            invoice_id,
        )

    async def can_take_action(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> bool:
        snapshot = await self.ownership_repo.get_ownership_snapshot(
            invoice_id,
        )

        if snapshot is None:
            return False

        if await self.is_unassigned(
            invoice_id,
        ):
            return False

        if snapshot.invoice_status == InvoiceStatus.ESCALATED:
            return (
                user_role == UserRole.FINANCE_MANAGER
                and snapshot.assigned_manager_id == user_id
            )

        if snapshot.assigned_manager_id is not None:
            return (
                user_role == UserRole.FINANCE_MANAGER
                and snapshot.assigned_manager_id == user_id
            )

        if user_role == UserRole.FINANCE_ASSOCIATE:
            return await self.is_associate_owner(
                associate_id=user_id,
                invoice_id=invoice_id,
            )

        return False

    async def ensure_can_take_action(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        if not await self.can_take_action(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            raise InvoiceAccessDeniedError()

    async def can_approve(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> bool:
        if not await self.can_take_action(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            return False

        snapshot = await self.ownership_repo.get_ownership_snapshot(
            invoice_id,
        )

        if snapshot is None:
            return False

        if snapshot.validation_outcome != InvoiceValidationOutcome.APPROVED:
            return False

        if snapshot.invoice_status == InvoiceStatus.UNDER_REVIEW:
            return True

        return snapshot.invoice_status == InvoiceStatus.ESCALATED

    async def ensure_can_approve(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        if not await self.can_approve(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            raise InvoiceAccessDeniedError()
