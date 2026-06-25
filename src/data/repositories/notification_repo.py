from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update

from src.data.models.postgres.notifications import Notification
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class NotificationRow:
    id: UUID
    user_id: UUID
    invoice_id: UUID | None
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationRepository(BaseRepository):
    async def create(
        self,
        *,
        user_id: UUID,
        invoice_id: UUID | None,
        title: str,
        message: str,
    ) -> NotificationRow:
        notification = Notification(
            user_id=user_id,
            invoice_id=invoice_id,
            title=title,
            message=message,
            is_read=False,
        )
        self.session.add(
            notification,
        )
        await self.session.flush()

        return NotificationRow(
            id=notification.id,
            user_id=notification.user_id,
            invoice_id=notification.invoice_id,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[NotificationRow], int]:
        base_filter = Notification.user_id == user_id

        count_result = await self.execute(
            select(
                func.count(),
            )
            .select_from(
                Notification,
            )
            .where(
                base_filter,
            ),
        )
        total_records = int(
            count_result.scalar_one(),
        )

        result = await self.execute(
            select(
                Notification,
            )
            .where(
                base_filter,
            )
            .order_by(
                Notification.created_at.desc(),
            )
            .offset(
                offset,
            )
            .limit(
                limit,
            ),
        )

        rows = [
            NotificationRow(
                id=notification.id,
                user_id=notification.user_id,
                invoice_id=notification.invoice_id,
                title=notification.title,
                message=notification.message,
                is_read=notification.is_read,
                created_at=notification.created_at,
            )
            for notification in result.scalars().all()
        ]

        return rows, total_records

    async def count_unread(
        self,
        user_id: UUID,
    ) -> int:
        result = await self.execute(
            select(
                func.count(),
            )
            .select_from(
                Notification,
            )
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(
                    False,
                ),
            ),
        )

        return int(
            result.scalar_one(),
        )

    async def get_by_id(
        self,
        notification_id: UUID,
    ) -> NotificationRow | None:
        result = await self.execute(
            select(
                Notification,
            ).where(
                Notification.id == notification_id,
            ),
        )
        notification = result.scalar_one_or_none()

        if notification is None:
            return None

        return NotificationRow(
            id=notification.id,
            user_id=notification.user_id,
            invoice_id=notification.invoice_id,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )

    async def mark_read(
        self,
        notification_id: UUID,
    ) -> None:
        await self.execute(
            update(
                Notification,
            )
            .where(
                Notification.id == notification_id,
            )
            .values(
                is_read=True,
                updated_at=func.now(),
            ),
        )

    async def mark_all_read(
        self,
        user_id: UUID,
    ) -> None:
        await self.execute(
            update(
                Notification,
            )
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(
                    False,
                ),
            )
            .values(
                is_read=True,
                updated_at=func.now(),
            ),
        )
