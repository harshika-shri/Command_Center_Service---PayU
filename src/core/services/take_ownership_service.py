from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.access_exc import (
    InvoiceAccessDeniedError,
)
from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.services.invoice_ownership_service import (
    InvoiceOwnershipService,
)
from src.core.services.notification_service import (
    NotificationService,
)
from src.core.sse.sse_event_publisher import SSEEventPublisher
from src.data.models.postgres.enums import (
    UserRole,
)
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)
from src.data.repositories.user_repo import (
    UserRepository,
)
from src.schemas.ownership_schema import (
    TakeOwnershipRequest,
    TakeOwnershipResponse,
)


class TakeOwnershipService:
    SUCCESS_MESSAGE = "Invoice ownership claimed successfully."

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.ownership_repo = InvoiceOwnershipRepository(
            session,
        )
        self.ownership_service = InvoiceOwnershipService(
            session,
        )
        self.user_repo = UserRepository(
            session,
        )
        self.audit_log_service = AuditLogService(
            session,
        )
        self.notification_service = NotificationService(
            session,
        )

    async def take_ownership(
        self,
        invoice_id: UUID,
        request: TakeOwnershipRequest,
    ) -> TakeOwnershipResponse:
        snapshot = await self.ownership_repo.get_ownership_snapshot(
            invoice_id,
        )

        if snapshot is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        manager = await self.user_repo.get_user_by_id(
            request.manager_id,
        )

        if (
            manager is None
            or not manager.is_active
            or manager.role != UserRole.FINANCE_MANAGER
        ):
            raise InvoiceAccessDeniedError(
                "Only an active Finance Manager may claim invoice ownership.",
            )

        if snapshot.assigned_manager_id is not None:
            raise InvoiceAccessDeniedError(
                "Invoice already has an assigned manager.",
            )

        if await self.ownership_repo.has_associate_ownership(
            invoice_id,
        ):
            raise InvoiceAccessDeniedError(
                "Invoice is already owned by a Finance Associate.",
            )

        await self.ownership_repo.assign_manager(
            invoice_id=invoice_id,
            manager_id=request.manager_id,
        )

        await self.audit_log_service.create_audit_log(
            AuditLogCreatePayload(
                invoice_id=invoice_id,
                action="TAKE_OWNERSHIP",
                old_status=(
                    snapshot.invoice_status.value
                    if snapshot.invoice_status is not None
                    else None
                ),
                new_status=(
                    snapshot.invoice_status.value
                    if snapshot.invoice_status is not None
                    else None
                ),
                remarks="Finance Manager claimed invoice ownership.",
                performed_by=request.manager_id,
            ),
        )

        await self.notification_service.notify_ownership_claimed(
            invoice_id=invoice_id,
            manager_id=request.manager_id,
        )

        await SSEEventPublisher.schedule_take_ownership_events(
            self.ownership_repo.session,
            invoice_id=invoice_id,
            manager_id=request.manager_id,
            invoice_status=snapshot.invoice_status,
            validation_outcome=snapshot.validation_outcome,
        )

        return TakeOwnershipResponse(
            invoice_id=invoice_id,
            assigned_manager_id=request.manager_id,
            message=self.SUCCESS_MESSAGE,
        )
