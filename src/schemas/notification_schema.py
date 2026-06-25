from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: UUID
    invoice_id: UUID | None
    title: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationUnreadCountResponse(BaseModel):
    count: int


class MarkNotificationReadResponse(BaseModel):
    notification_id: UUID
    is_read: bool
    message: str


class MarkAllNotificationsReadResponse(BaseModel):
    message: str


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total_records: int
    total_pages: int
    current_page: int
    page_size: int
    page: int
