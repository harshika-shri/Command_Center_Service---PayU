from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.postgres.company_master import CompanyMaster
from src.data.models.postgres.invoice_extracted_vendor import InvoiceExtractedVendor
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class InvoiceHeaderRow:
    invoice_id: UUID
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None
    subtotal_amount: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    payment_terms: str | None
    notes: str | None
    invoice_status: str | None
    validation_outcome: str | None
    received_email: str | None
    created_at: datetime
    updated_at: datetime
    vendor_name: str | None
    vendor_code: str | None
    vendor_gstin: str | None
    vendor_email: str | None
    company_name: str | None
    company_code: str | None
    company_gstin: str | None


class InvoiceHeaderRepository(BaseRepository):
    async def get_header(
        self,
        invoice_id: UUID,
    ) -> InvoiceHeaderRow | None:
        result = await self.execute(
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_date,
                Invoice.due_date,
                Invoice.subtotal_amount,
                Invoice.tax_amount,
                Invoice.total_amount,
                Invoice.payment_terms,
                Invoice.notes,
                Invoice.invoice_status,
                Invoice.validation_outcome,
                Invoice.received_email,
                Invoice.created_at,
                Invoice.updated_at,
                # Vendor: prefer VendorMaster, fall back to InvoiceExtractedVendor
                func.coalesce(
                    VendorMaster.vendor_name,
                    InvoiceExtractedVendor.vendor_name,
                ).label('vendor_name'),
                VendorMaster.vendor_code.label('vendor_code'),
                func.coalesce(
                    VendorMaster.gstin,
                    InvoiceExtractedVendor.vendor_gstin,
                ).label('vendor_gstin'),
                func.coalesce(
                    VendorMaster.email,
                    InvoiceExtractedVendor.vendor_email,
                ).label('vendor_email'),
                # Company
                CompanyMaster.company_name,
                CompanyMaster.company_code,
                CompanyMaster.gstin.label('company_gstin'),
            )
            .select_from(Invoice)
            .outerjoin(VendorMaster, Invoice.vendor_id == VendorMaster.id)
            .outerjoin(
                InvoiceExtractedVendor,
                Invoice.id == InvoiceExtractedVendor.invoice_id,
            )
            .outerjoin(CompanyMaster, Invoice.company_id == CompanyMaster.id)
            .where(Invoice.id == invoice_id),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return InvoiceHeaderRow(
            invoice_id=row.id,
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
            due_date=row.due_date,
            subtotal_amount=row.subtotal_amount,
            tax_amount=row.tax_amount,
            total_amount=row.total_amount,
            payment_terms=row.payment_terms,
            notes=row.notes,
            invoice_status=(
                row.invoice_status.value if row.invoice_status is not None else None
            ),
            validation_outcome=(
                row.validation_outcome.value
                if row.validation_outcome is not None
                else None
            ),
            received_email=row.received_email,
            created_at=row.created_at,
            updated_at=row.updated_at,
            vendor_name=row.vendor_name,
            vendor_code=row.vendor_code,
            vendor_gstin=row.vendor_gstin,
            vendor_email=row.vendor_email,
            company_name=row.company_name,
            company_code=row.company_code,
            company_gstin=row.company_gstin,
        )
