from __future__ import annotations

from src.core.exceptions.base_exc import AppException


class InvoiceEscalationConflictError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=409,
            error_code="INVOICE_ESCALATION_CONFLICT",
        )


class InvoiceEscalationValidationError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=400,
            error_code="INVOICE_ESCALATION_VALIDATION_ERROR",
        )
