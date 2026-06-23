from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.invoice_access_service import (
    InvoiceAccessService,
)
from src.data.repositories.invoice_extraction_repo import (
    InvoiceExtractionData,
    InvoiceExtractionRepository,
)
from src.schemas.invoice_review_schema import (
    ConfidenceScoreDetails,
    ExtractedVendorDetails,
    InvoiceEmailDetails,
    InvoiceExtractionResponse,
    InvoiceLineItemDetails,
)
from src.utils.decimal_utils import decimal_to_float


class InvoiceExtractionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.access_service = InvoiceAccessService(
            session,
        )
        self.extraction_repo = InvoiceExtractionRepository(
            session,
        )

    async def get_extraction(
        self,
        invoice_id: UUID,
        *,
        require_exists: bool = True,
    ) -> InvoiceExtractionResponse:
        if require_exists:
            await self.access_service.ensure_invoice_exists(
                invoice_id,
            )

        data = await self.extraction_repo.get_extraction_data(
            invoice_id,
        )

        return self._map_extraction(
            data,
        )

    @staticmethod
    def _map_extraction(
        data: InvoiceExtractionData,
    ) -> InvoiceExtractionResponse:
        email_details = None

        if data.email is not None:
            email_details = InvoiceEmailDetails(
                received_from=data.email.received_from,
                subject=data.email.subject,
                body_text=data.email.body_text,
                attachment_filename=data.email.attachment_filename,
            )

        vendor_details = None

        if data.vendor is not None:
            vendor_details = ExtractedVendorDetails(
                vendor_name=data.vendor.vendor_name,
                vendor_gstin=data.vendor.vendor_gstin,
                vendor_address=data.vendor.vendor_address,
                vendor_email=data.vendor.vendor_email,
                vendor_phone=data.vendor.vendor_phone,
                bank_account_number=data.vendor.bank_account_number,
                bank_name=data.vendor.bank_name,
                ifsc_code=data.vendor.ifsc_code,
                account_holder_name=data.vendor.account_holder_name,
            )

        return InvoiceExtractionResponse(
            email_details=email_details,
            vendor_details=vendor_details,
            line_items=[
                InvoiceLineItemDetails(
                    id=item.id,
                    line_number=item.line_number,
                    item_code=item.item_code,
                    item_description=item.item_description,
                    uom=item.uom,
                    quantity_billed=decimal_to_float(
                        item.quantity_billed,
                    )
                    or 0.0,
                    unit_price=decimal_to_float(
                        item.unit_price,
                    )
                    or 0.0,
                    discount_amount=decimal_to_float(
                        item.discount_amount,
                    ),
                    tax_details=item.tax_details,
                    hsn_sac_code=item.hsn_sac_code,
                    line_total=decimal_to_float(
                        item.line_total,
                    )
                    or 0.0,
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
                for item in data.line_items
            ],
            confidence_scores=[
                ConfidenceScoreDetails(
                    id=record.id,
                    field_name=record.field_name,
                    extracted_value=record.extracted_value,
                    confidence_score=decimal_to_float(
                        record.confidence_score,
                    )
                    or 0.0,
                    is_flagged=record.is_flagged,
                    created_at=record.created_at,
                )
                for record in data.confidence_scores
            ],
        )
