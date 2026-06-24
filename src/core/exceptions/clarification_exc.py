from __future__ import annotations

from src.core.exceptions.base_exc import AppException


class ClarificationConflictError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=409,
            error_code="CLARIFICATION_CONFLICT",
        )


class ClarificationValidationError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=400,
            error_code="CLARIFICATION_VALIDATION_ERROR",
        )


class ClarificationSendGridError(AppException):
    def __init__(
        self,
        detail: str,
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=500,
            error_code="CLARIFICATION_SENDGRID_ERROR",
        )
