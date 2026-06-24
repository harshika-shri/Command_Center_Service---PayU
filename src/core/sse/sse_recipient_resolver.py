from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)


class SSERecipientResolver:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.ownership_repo = InvoiceOwnershipRepository(
            session,
        )

    async def resolve_invoice_recipients(
        self,
        invoice_id: UUID,
    ) -> frozenset[UUID]:
        recipients: set[UUID] = set()

        associate_id = await self.ownership_repo.get_associate_owner_id(
            invoice_id,
        )

        if associate_id is not None:
            recipients.add(
                associate_id,
            )

        snapshot = await self.ownership_repo.get_ownership_snapshot(
            invoice_id,
        )

        if (
            snapshot is not None
            and snapshot.assigned_manager_id is not None
        ):
            recipients.add(
                snapshot.assigned_manager_id,
            )

        return frozenset(
            recipients,
        )
