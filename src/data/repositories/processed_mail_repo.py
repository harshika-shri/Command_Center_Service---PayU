from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, func, literal, or_, select, union_all

from src.data.models.postgres.invoice_email import InvoiceEmail
from src.data.models.postgres.processed_gmail_message import (
    ProcessedGmailMessage,
)
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class RecentMailRow:
    message_id: str
    mailbox: str | None
    subject: str | None
    received_from: str | None
    attachment_filename: str | None
    processed_at: datetime
    invoice_id: UUID | None


class ProcessedMailRepository(BaseRepository):
    async def list_recent_mail(
        self,
        *,
        mailbox: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RecentMailRow], int]:
        processed_stmt = (
            select(
                ProcessedGmailMessage.message_id.label(
                    "message_id",
                ),
                ProcessedGmailMessage.email_address.label(
                    "mailbox",
                ),
                InvoiceEmail.subject.label(
                    "subject",
                ),
                InvoiceEmail.received_from.label(
                    "received_from",
                ),
                InvoiceEmail.attachment_filename.label(
                    "attachment_filename",
                ),
                ProcessedGmailMessage.created_at.label(
                    "processed_at",
                ),
                InvoiceEmail.invoice_id.label(
                    "invoice_id",
                ),
            )
            .select_from(
                ProcessedGmailMessage,
            )
            .outerjoin(
                InvoiceEmail,
                or_(
                    InvoiceEmail.message_id
                    == ProcessedGmailMessage.message_id,
                    InvoiceEmail.message_id.like(
                        func.concat(
                            ProcessedGmailMessage.message_id,
                            literal("::%"),
                        ),
                    ),
                ),
            )
        )

        if mailbox is not None:
            processed_stmt = processed_stmt.where(
                ProcessedGmailMessage.email_address
                == mailbox,
            )

        legacy_stmt = (
            select(
                InvoiceEmail.message_id.label(
                    "message_id",
                ),
                literal(
                    None,
                    type_=String(255),
                ).label(
                    "mailbox",
                ),
                InvoiceEmail.subject.label(
                    "subject",
                ),
                InvoiceEmail.received_from.label(
                    "received_from",
                ),
                InvoiceEmail.attachment_filename.label(
                    "attachment_filename",
                ),
                InvoiceEmail.created_at.label(
                    "processed_at",
                ),
                InvoiceEmail.invoice_id.label(
                    "invoice_id",
                ),
            )
            .where(
                ~InvoiceEmail.message_id.in_(
                    select(
                        ProcessedGmailMessage.message_id,
                    ),
                ),
                ~func.split_part(
                    InvoiceEmail.message_id,
                    literal("::"),
                    literal(1),
                ).in_(
                    select(
                        ProcessedGmailMessage.message_id,
                    ),
                ),
            )
        )

        combined = union_all(
            processed_stmt,
            legacy_stmt,
        ).subquery()

        count_stmt = select(
            func.count(),
        ).select_from(
            combined,
        )
        count_result = await self.execute(
            count_stmt,
        )
        total = int(
            count_result.scalar_one(),
        )

        rows_stmt = (
            select(
                combined,
            )
            .order_by(
                combined.c.processed_at.desc(),
            )
            .limit(
                limit,
            )
            .offset(
                offset,
            )
        )
        result = await self.execute(
            rows_stmt,
        )

        items = [
            RecentMailRow(
                message_id=row.message_id,
                mailbox=row.mailbox,
                subject=row.subject,
                received_from=row.received_from,
                attachment_filename=row.attachment_filename,
                processed_at=row.processed_at,
                invoice_id=row.invoice_id,
            )
            for row in result.all()
        ]

        return items, total
