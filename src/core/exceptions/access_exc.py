from __future__ import annotations

from src.core.exceptions.base_exc import AppException


class InvoiceAccessDeniedError(AppException):
    def __init__(
        self,
        detail: str = (
            "You do not have permission to act on this invoice."
        ),
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=403,
            error_code="INVOICE_ACCESS_DENIED",
        )
