from __future__ import annotations

from src.core.exceptions.base_exc import AppException


class InvoiceNotFoundError(AppException):
    def __init__(
        self,
        invoice_id: str,
    ) -> None:
        super().__init__(
            detail=f"Invoice not found: {invoice_id}",
            status_code=404,
            error_code="INVOICE_NOT_FOUND",
        )


class ValidationEventProcessingError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=500,
            error_code="VALIDATION_EVENT_PROCESSING_ERROR",
        )
