from __future__ import annotations

from src.core.exceptions.base_exc import AppException


class NotificationAccessDeniedError(AppException):
    def __init__(
        self,
        detail: str = "You do not have access to this notification.",
    ) -> None:
        super().__init__(
            detail=detail,
            status_code=403,
            error_code="NOTIFICATION_ACCESS_DENIED",
        )
