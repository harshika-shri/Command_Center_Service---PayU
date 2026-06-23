from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.invoice_access_service import (
    InvoiceAccessService,
)
from src.data.repositories.invoice_header_repo import (
    InvoiceHeaderRepository,
    InvoiceHeaderRow,
)
from src.schemas.invoice_review_schema import (
    InvoiceCompanySummary,
    InvoiceHeaderResponse,
    InvoiceVendorSummary,
)
from src.utils.decimal_utils import decimal_to_float


class InvoiceHeaderService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.access_service = InvoiceAccessService(
            session,
        )
        self.header_repo = InvoiceHeaderRepository(
            session,
        )

    async def get_header(
        self,
        invoice_id: UUID,
        *,
        require_exists: bool = True,
    ) -> InvoiceHeaderResponse:
        if require_exists:
            await self.access_service.ensure_invoice_exists(
                invoice_id,
            )

        row = await self.header_repo.get_header(
            invoice_id,
        )

        if row is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        return self._map_header(
            row,
        )

    @staticmethod
    def _map_header(
        row: InvoiceHeaderRow,
    ) -> InvoiceHeaderResponse:
        vendor = None

        if any(
            (
                row.vendor_name,
                row.vendor_code,
                row.vendor_gstin,
                row.vendor_email,
            ),
        ):
            vendor = InvoiceVendorSummary(
                vendor_name=row.vendor_name,
                vendor_code=row.vendor_code,
                gstin=row.vendor_gstin,
                email=row.vendor_email,
            )

        company = None

        if any(
            (
                row.company_name,
                row.company_code,
                row.company_gstin,
            ),
        ):
            company = InvoiceCompanySummary(
                company_name=row.company_name,
                company_code=row.company_code,
                gstin=row.company_gstin,
            )

        return InvoiceHeaderResponse(
            invoice_id=row.invoice_id,
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
            due_date=row.due_date,
            vendor=vendor,
            company=company,
            subtotal_amount=decimal_to_float(
                row.subtotal_amount,
            ),
            tax_amount=decimal_to_float(
                row.tax_amount,
            ),
            total_amount=decimal_to_float(
                row.total_amount,
            ),
            payment_terms=row.payment_terms,
            notes=row.notes,
            invoice_status=row.invoice_status,
            validation_outcome=row.validation_outcome,
            received_email=row.received_email,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
