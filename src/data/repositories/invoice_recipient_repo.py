from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.config.settings import settings
from src.data.models.postgres.invoice_email import InvoiceEmail
from src.data.models.postgres.invoice_extracted_vendor import InvoiceExtractedVendor
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository


class InvoiceRecipientRepository(BaseRepository):
    async def get_recipient_email(
        self,
        invoice_id: UUID,
        *,
        sender_only: bool = False,
    ) -> str | None:
        """Return the email address to send vendor communications to.

        When sender_only is True (clarification/rejection), only the original
        invoice sender email is returned — never vendor master/extracted emails.

        Priority (sender_only=True):
        1. invoice_emails.received_from
        2. invoices.received_email
        3. VENDOR_EMAIL_FALLBACK setting (only when no sender email found)

        Priority (sender_only=False):
        1–2 as above, then vendor_master.email, then extracted vendor email.
        """
        sender_email = await self._get_sender_email(invoice_id)
        if sender_email:
            return sender_email

        if sender_only:
            fallback = settings.VENDOR_EMAIL_FALLBACK.strip()
            return fallback or None

        result = await self.execute(
            select(
                VendorMaster.email.label('vendor_master_email'),
                InvoiceExtractedVendor.vendor_email.label('extracted_vendor_email'),
            )
            .select_from(Invoice)
            .outerjoin(VendorMaster, Invoice.vendor_id == VendorMaster.id)
            .outerjoin(
                InvoiceExtractedVendor,
                Invoice.id == InvoiceExtractedVendor.invoice_id,
            )
            .where(Invoice.id == invoice_id),
        )
        row = result.one_or_none()

        if row is None:
            return None

        if row.vendor_master_email:
            return row.vendor_master_email

        return row.extracted_vendor_email

    async def _get_sender_email(
        self,
        invoice_id: UUID,
    ) -> str | None:
        email_result = await self.execute(
            select(InvoiceEmail.received_from).where(
                InvoiceEmail.invoice_id == invoice_id,
            ),
        )
        received_from = email_result.scalar_one_or_none()
        if received_from:
            return received_from.strip()

        invoice_result = await self.execute(
            select(Invoice.received_email).where(
                Invoice.id == invoice_id,
            ),
        )
        received_email = invoice_result.scalar_one_or_none()
        if received_email:
            return received_email.strip()

        return None
