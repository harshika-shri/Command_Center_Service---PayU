from __future__ import annotations

from src.core.exceptions.base_exc import AppException


class InvoiceRejectionConflictError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=409,
            error_code="INVOICE_REJECTION_CONFLICT",
        )


class InvoiceRejectionValidationError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=400,
            error_code="INVOICE_REJECTION_VALIDATION_ERROR",
        )


class RejectionDraftGenerationError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=500,
            error_code="REJECTION_DRAFT_GENERATION_ERROR",
        )
