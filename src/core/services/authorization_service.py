from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.access_exc import (
    InvoiceAccessDeniedError,
)
from src.core.services.invoice_ownership_service import (
    InvoiceOwnershipService,
)
from src.core.workflow.invoice_workflow_buckets import (
    is_eligible_for_business_rejection,
    is_eligible_for_clarification,
    is_eligible_for_escalation,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
    UserRole,
)


class AuthorizationService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.ownership_service = InvoiceOwnershipService(
            session,
        )

    async def can_view_invoice(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> bool:
        if user_role == UserRole.FINANCE_ASSOCIATE:
            return await self.ownership_service.is_associate_owner(
                associate_id=user_id,
                invoice_id=invoice_id,
            )

        if user_role == UserRole.FINANCE_MANAGER:
            if await self.ownership_service.is_manager_owner(
                manager_id=user_id,
                invoice_id=invoice_id,
            ):
                return True

            return await self.ownership_service.is_unassigned(
                invoice_id,
            )

        return False

    async def ensure_can_view_invoice(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        if not await self.can_view_invoice(
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
        return await self.ownership_service.can_approve(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        )

    async def ensure_can_approve(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        await self.ownership_service.ensure_can_approve(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        )

    async def can_reject(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> bool:
        if not await self.ownership_service.can_take_action(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            return False

        snapshot = (
            await self.ownership_service.ownership_repo.get_ownership_snapshot(
                invoice_id,
            )
        )

        if snapshot is None:
            return False

        return is_eligible_for_business_rejection(
            snapshot.invoice_status,
        )

    async def ensure_can_reject(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        if not await self.can_reject(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            raise InvoiceAccessDeniedError()

    async def can_clarify(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> bool:
        if not await self.ownership_service.can_take_action(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            return False

        snapshot = (
            await self.ownership_service.ownership_repo.get_ownership_snapshot(
                invoice_id,
            )
        )

        if snapshot is None:
            return False

        return is_eligible_for_clarification(
            invoice_status=snapshot.invoice_status,
            validation_outcome=snapshot.validation_outcome,
        )

    async def ensure_can_clarify(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        if not await self.can_clarify(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            raise InvoiceAccessDeniedError()

    async def can_escalate(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> bool:
        if user_role != UserRole.FINANCE_ASSOCIATE:
            return False

        if not await self.ownership_service.can_take_action(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            return False

        snapshot = (
            await self.ownership_service.ownership_repo.get_ownership_snapshot(
                invoice_id,
            )
        )

        if snapshot is None:
            return False

        return is_eligible_for_escalation(
            snapshot.invoice_status,
        )

    async def ensure_can_escalate(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        if not await self.can_escalate(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            raise InvoiceAccessDeniedError()

    async def can_take_ownership(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> bool:
        if user_role != UserRole.FINANCE_MANAGER:
            return False

        snapshot = (
            await self.ownership_service.ownership_repo.get_ownership_snapshot(
                invoice_id,
            )
        )

        if snapshot is None:
            return False

        if snapshot.assigned_manager_id is not None:
            return False

        if await self.ownership_service.ownership_repo.has_associate_ownership(
            invoice_id,
        ):
            return False

        return True

    async def ensure_can_take_ownership(
        self,
        *,
        user_id: UUID,
        user_role: UserRole,
        invoice_id: UUID,
    ) -> None:
        if not await self.can_take_ownership(
            user_id=user_id,
            user_role=user_role,
            invoice_id=invoice_id,
        ):
            raise InvoiceAccessDeniedError()
