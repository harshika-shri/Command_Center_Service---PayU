from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.notification_exc import (
    NotificationAccessDeniedError,
)
from src.data.models.postgres.invoices import Invoice
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)
from src.data.repositories.notification_repo import (
    NotificationRepository,
    NotificationRow,
)
from src.schemas.notification_schema import (
    MarkAllNotificationsReadResponse,
    MarkNotificationReadResponse,
    NotificationItem,
    NotificationUnreadCountResponse,
)

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.notification_repo = NotificationRepository(
            session,
        )
        self.ownership_repo = InvoiceOwnershipRepository(
            session,
        )

    async def list_notifications(
        self,
        user_id: UUID,
    ) -> list[NotificationItem]:
        rows = await self.notification_repo.list_by_user(
            user_id,
        )

        return [
            self._map_notification_row(
                row,
            )
            for row in rows
        ]

    async def get_unread_count(
        self,
        user_id: UUID,
    ) -> NotificationUnreadCountResponse:
        count = await self.notification_repo.count_unread(
            user_id,
        )

        return NotificationUnreadCountResponse(
            count=count,
        )

    async def mark_notification_read(
        self,
        *,
        user_id: UUID,
        notification_id: UUID,
    ) -> MarkNotificationReadResponse:
        notification = await self._get_owned_notification(
            user_id=user_id,
            notification_id=notification_id,
        )

        if not notification.is_read:
            await self.notification_repo.mark_read(
                notification_id,
            )

        return MarkNotificationReadResponse(
            notification_id=notification_id,
            is_read=True,
            message="Notification marked as read.",
        )

    async def mark_all_read(
        self,
        user_id: UUID,
    ) -> MarkAllNotificationsReadResponse:
        await self.notification_repo.mark_all_read(
            user_id,
        )

        return MarkAllNotificationsReadResponse(
            message="All notifications marked as read.",
        )

    async def notify_invoice_assigned(
        self,
        invoice_id: UUID,
    ) -> None:
        await self._safe_notify(
            action="invoice_assigned",
            invoice_id=invoice_id,
            notifier=lambda: self._create_invoice_assigned_notification(
                invoice_id,
            ),
        )

    async def notify_invoice_escalated(
        self,
        *,
        invoice_id: UUID,
        manager_id: UUID,
        associate_id: UUID | None,
    ) -> None:
        await self._safe_notify(
            action="invoice_escalated",
            invoice_id=invoice_id,
            notifier=lambda: self._create_invoice_escalated_notifications(
                invoice_id=invoice_id,
                manager_id=manager_id,
                associate_id=associate_id,
            ),
        )

    async def notify_ownership_claimed(
        self,
        *,
        invoice_id: UUID,
        manager_id: UUID,
    ) -> None:
        await self._safe_notify(
            action="ownership_claimed",
            invoice_id=invoice_id,
            notifier=lambda: self._create_ownership_claimed_notification(
                invoice_id=invoice_id,
                manager_id=manager_id,
            ),
        )

    async def notify_clarification_sent(
        self,
        invoice_id: UUID,
    ) -> None:
        await self._safe_notify(
            action="clarification_sent",
            invoice_id=invoice_id,
            notifier=lambda: self._create_clarification_sent_notification(
                invoice_id,
            ),
        )

    async def notify_invoice_approved(
        self,
        invoice_id: UUID,
    ) -> None:
        await self._safe_notify(
            action="invoice_approved",
            invoice_id=invoice_id,
            notifier=lambda: self._create_invoice_approved_notification(
                invoice_id,
            ),
        )

    async def notify_invoice_rejected(
        self,
        invoice_id: UUID,
    ) -> None:
        await self._safe_notify(
            action="invoice_rejected",
            invoice_id=invoice_id,
            notifier=lambda: self._create_invoice_rejected_notification(
                invoice_id,
            ),
        )

    async def _create_invoice_assigned_notification(
        self,
        invoice_id: UUID,
    ) -> None:
        associate_id = await self.ownership_repo.get_associate_owner_id(
            invoice_id,
        )

        if associate_id is None:
            return

        display_number = await self._get_invoice_display_number(
            invoice_id,
        )

        await self.notification_repo.create(
            user_id=associate_id,
            invoice_id=invoice_id,
            title="Invoice Assigned",
            message=(
                f"Invoice {display_number} requires your review."
            ),
        )

    async def _create_invoice_escalated_notifications(
        self,
        *,
        invoice_id: UUID,
        manager_id: UUID,
        associate_id: UUID | None,
    ) -> None:
        display_number = await self._get_invoice_display_number(
            invoice_id,
        )

        await self.notification_repo.create(
            user_id=manager_id,
            invoice_id=invoice_id,
            title="Invoice Escalated",
            message=(
                f"Invoice {display_number} has been escalated to you "
                "for review."
            ),
        )

        if associate_id is None:
            return

        await self.notification_repo.create(
            user_id=associate_id,
            invoice_id=invoice_id,
            title="Invoice Escalated",
            message=(
                f"Ownership of Invoice {display_number} has been "
                "transferred to Finance Manager for review."
            ),
        )

    async def _create_ownership_claimed_notification(
        self,
        *,
        invoice_id: UUID,
        manager_id: UUID,
    ) -> None:
        display_number = await self._get_invoice_display_number(
            invoice_id,
        )

        await self.notification_repo.create(
            user_id=manager_id,
            invoice_id=invoice_id,
            title="Invoice Assigned",
            message=(
                f"You are now responsible for Invoice {display_number}."
            ),
        )

    async def _create_clarification_sent_notification(
        self,
        invoice_id: UUID,
    ) -> None:
        owner_id = await self._resolve_invoice_owner_user_id(
            invoice_id,
        )

        if owner_id is None:
            return

        display_number = await self._get_invoice_display_number(
            invoice_id,
        )

        await self.notification_repo.create(
            user_id=owner_id,
            invoice_id=invoice_id,
            title="Clarification Sent",
            message=(
                f"Clarification request sent to vendor for Invoice "
                f"{display_number}."
            ),
        )

    async def _create_invoice_approved_notification(
        self,
        invoice_id: UUID,
    ) -> None:
        owner_id = await self._resolve_invoice_owner_user_id(
            invoice_id,
        )

        if owner_id is None:
            return

        display_number = await self._get_invoice_display_number(
            invoice_id,
        )

        await self.notification_repo.create(
            user_id=owner_id,
            invoice_id=invoice_id,
            title="Invoice Approved",
            message=(
                f"Invoice {display_number} has been approved and moved "
                "to Ready To Pay."
            ),
        )

    async def _create_invoice_rejected_notification(
        self,
        invoice_id: UUID,
    ) -> None:
        owner_id = await self._resolve_invoice_owner_user_id(
            invoice_id,
        )

        if owner_id is None:
            return

        display_number = await self._get_invoice_display_number(
            invoice_id,
        )

        await self.notification_repo.create(
            user_id=owner_id,
            invoice_id=invoice_id,
            title="Invoice Rejected",
            message=(
                f"Invoice {display_number} has been rejected."
            ),
        )

    async def _resolve_invoice_owner_user_id(
        self,
        invoice_id: UUID,
    ) -> UUID | None:
        snapshot = await self.ownership_repo.get_ownership_snapshot(
            invoice_id,
        )

        if snapshot is None:
            return None

        if snapshot.assigned_manager_id is not None:
            return snapshot.assigned_manager_id

        return await self.ownership_repo.get_associate_owner_id(
            invoice_id,
        )

    async def _get_invoice_display_number(
        self,
        invoice_id: UUID,
    ) -> str:
        result = await self.notification_repo.execute(
            select(
                Invoice.invoice_number,
            ).where(
                Invoice.id == invoice_id,
            ),
        )
        invoice_number = result.scalar_one_or_none()

        if invoice_number:
            return invoice_number

        return f"INV-{str(invoice_id)[:8].upper()}"

    async def _get_owned_notification(
        self,
        *,
        user_id: UUID,
        notification_id: UUID,
    ) -> NotificationRow:
        notification = await self.notification_repo.get_by_id(
            notification_id,
        )

        if notification is None:
            raise NotificationAccessDeniedError(
                "Notification not found.",
            )

        if notification.user_id != user_id:
            raise NotificationAccessDeniedError()

        return notification

    async def _safe_notify(
        self,
        *,
        action: str,
        invoice_id: UUID,
        notifier: Callable[[], Awaitable[None]],
    ) -> None:
        try:
            await notifier()
        except Exception:
            logger.exception(
                "Failed to create notification action=%s invoice_id=%s",
                action,
                invoice_id,
            )

    @staticmethod
    def _map_notification_row(
        row: NotificationRow,
    ) -> NotificationItem:
        return NotificationItem(
            id=row.id,
            invoice_id=row.invoice_id,
            title=row.title,
            message=row.message,
            is_read=row.is_read,
            created_at=row.created_at,
        )
