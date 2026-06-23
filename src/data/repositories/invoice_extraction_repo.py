from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.extraction_field_confidence import (
    ExtractionFieldConfidence,
)
from src.data.models.postgres.invoice_email import InvoiceEmail
from src.data.models.postgres.invoice_extracted_vendor import (
    InvoiceExtractedVendor,
)
from src.data.models.postgres.invoice_line_items import InvoiceLineItem
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class InvoiceEmailRow:
    received_from: str
    subject: str | None
    body_text: str | None
    attachment_filename: str | None


@dataclass(frozen=True, slots=True)
class ExtractedVendorRow:
    vendor_name: str | None
    vendor_gstin: str | None
    vendor_address: str | None
    vendor_email: str | None
    vendor_phone: str | None
    bank_account_number: str | None
    bank_name: str | None
    ifsc_code: str | None
    account_holder_name: str | None


@dataclass(frozen=True, slots=True)
class InvoiceLineItemRow:
    id: UUID
    line_number: int
    item_code: str | None
    item_description: str | None
    uom: str | None
    quantity_billed: Decimal
    unit_price: Decimal
    discount_amount: Decimal | None
    tax_details: dict[str, Any] | None
    hsn_sac_code: str | None
    line_total: Decimal
    is_item_code_matched: bool | None
    is_unauthorized_extra_item: bool | None
    is_hsn_matched: bool | None
    is_line_total_correct: bool | None
    is_unit_price_matched: bool | None
    is_quantity_valid: bool | None
    is_uom_matched: bool | None
    is_tax_correct: bool | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConfidenceScoreRow:
    id: UUID
    field_name: str
    extracted_value: str | None
    confidence_score: Decimal
    is_flagged: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class InvoiceExtractionData:
    email: InvoiceEmailRow | None
    vendor: ExtractedVendorRow | None
    line_items: list[InvoiceLineItemRow]
    confidence_scores: list[ConfidenceScoreRow]


class InvoiceExtractionRepository(BaseRepository):
    async def get_extraction_data(
        self,
        invoice_id: UUID,
    ) -> InvoiceExtractionData:
        email = await self._get_email(
            invoice_id,
        )
        vendor = await self._get_vendor(
            invoice_id,
        )
        line_items = await self._get_line_items(
            invoice_id,
        )
        confidence_scores = await self._get_confidence_scores(
            invoice_id,
        )

        return InvoiceExtractionData(
            email=email,
            vendor=vendor,
            line_items=line_items,
            confidence_scores=confidence_scores,
        )

    async def _get_email(
        self,
        invoice_id: UUID,
    ) -> InvoiceEmailRow | None:
        result = await self.execute(
            select(
                InvoiceEmail.received_from,
                InvoiceEmail.subject,
                InvoiceEmail.body_text,
                InvoiceEmail.attachment_filename,
            ).where(
                InvoiceEmail.invoice_id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return InvoiceEmailRow(
            received_from=row.received_from,
            subject=row.subject,
            body_text=row.body_text,
            attachment_filename=row.attachment_filename,
        )

    async def _get_vendor(
        self,
        invoice_id: UUID,
    ) -> ExtractedVendorRow | None:
        result = await self.execute(
            select(
                InvoiceExtractedVendor.vendor_name,
                InvoiceExtractedVendor.vendor_gstin,
                InvoiceExtractedVendor.vendor_address,
                InvoiceExtractedVendor.vendor_email,
                InvoiceExtractedVendor.vendor_phone,
                InvoiceExtractedVendor.bank_account_number,
                InvoiceExtractedVendor.bank_name,
                InvoiceExtractedVendor.ifsc_code,
                InvoiceExtractedVendor.account_holder_name,
            ).where(
                InvoiceExtractedVendor.invoice_id == invoice_id,
            ),
        )
        row = result.one_or_none()

        if row is None:
            return None

        return ExtractedVendorRow(
            vendor_name=row.vendor_name,
            vendor_gstin=row.vendor_gstin,
            vendor_address=row.vendor_address,
            vendor_email=row.vendor_email,
            vendor_phone=row.vendor_phone,
            bank_account_number=row.bank_account_number,
            bank_name=row.bank_name,
            ifsc_code=row.ifsc_code,
            account_holder_name=row.account_holder_name,
        )

    async def _get_line_items(
        self,
        invoice_id: UUID,
    ) -> list[InvoiceLineItemRow]:
        result = await self.execute(
            select(InvoiceLineItem)
            .where(
                InvoiceLineItem.invoice_id == invoice_id,
            )
            .order_by(
                InvoiceLineItem.line_number.asc(),
            ),
        )

        return [
            InvoiceLineItemRow(
                id=item.id,
                line_number=item.line_number,
                item_code=item.item_code,
                item_description=item.item_description,
                uom=item.uom,
                quantity_billed=item.quantity_billed,
                unit_price=item.unit_price,
                discount_amount=item.discount_amount,
                tax_details=item.tax_details,
                hsn_sac_code=item.hsn_sac_code,
                line_total=item.line_total,
                is_item_code_matched=item.is_item_code_matched,
                is_unauthorized_extra_item=item.is_unauthorized_extra_item,
                is_hsn_matched=item.is_hsn_matched,
                is_line_total_correct=item.is_line_total_correct,
                is_unit_price_matched=item.is_unit_price_matched,
                is_quantity_valid=item.is_quantity_valid,
                is_uom_matched=item.is_uom_matched,
                is_tax_correct=item.is_tax_correct,
                created_at=item.created_at,
            )
            for item in result.scalars().all()
        ]

    async def _get_confidence_scores(
        self,
        invoice_id: UUID,
    ) -> list[ConfidenceScoreRow]:
        result = await self.execute(
            select(ExtractionFieldConfidence)
            .where(
                ExtractionFieldConfidence.invoice_id == invoice_id,
            )
            .order_by(
                ExtractionFieldConfidence.field_name.asc(),
            ),
        )

        return [
            ConfidenceScoreRow(
                id=record.id,
                field_name=record.field_name,
                extracted_value=record.extracted_value,
                confidence_score=record.confidence_score,
                is_flagged=record.is_flagged,
                created_at=record.created_at,
            )
            for record in result.scalars().all()
        ]
