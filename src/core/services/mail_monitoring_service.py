from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.repositories.processed_mail_repo import (
    ProcessedMailRepository,
    RecentMailRow,
)
from src.schemas.mail_monitoring_schema import (
    RecentMailItem,
    RecentMailListResponse,
)


class MailMonitoringService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.repo = ProcessedMailRepository(
            session,
        )

    async def list_recent_mail(
        self,
        *,
        mailbox: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> RecentMailListResponse:
        rows, total = await self.repo.list_recent_mail(
            mailbox=mailbox,
            limit=limit,
            offset=offset,
        )

        return RecentMailListResponse(
            items=[
                self._to_item(
                    row,
                )
                for row in rows
            ],
            total=total,
        )

    @staticmethod
    def _to_item(
        row: RecentMailRow,
    ) -> RecentMailItem:
        has_attachment = bool(
            row.attachment_filename,
        )
        has_invoice = row.invoice_id is not None

        if has_invoice:
            mail_status = "invoice_created"
        elif has_attachment:
            mail_status = "attachment_processed"
        else:
            mail_status = "no_attachment"

        return RecentMailItem(
            message_id=row.message_id,
            mailbox=row.mailbox,
            subject=row.subject,
            received_from=row.received_from,
            attachment_filename=row.attachment_filename,
            processed_at=row.processed_at,
            has_invoice=has_invoice,
            mail_status=mail_status,
            invoice_id=row.invoice_id,
        )
