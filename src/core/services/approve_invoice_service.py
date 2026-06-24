from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.approval_exc import (
    InvoiceApprovalConflictError,
    InvoiceApprovalValidationError,
)
from src.core.exceptions.workflow_exc import (
    InvoiceNotFoundError,
)
from src.core.services.allocation_finalization_service import (
    AllocationFinalizationService,
)
from src.core.services.audit_log_service import (
    AuditLogCreatePayload,
    AuditLogService,
)
from src.core.workflow.invoice_workflow_buckets import (
    is_ready_for_approval,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.repositories.approval_repo import (
    ApprovalRepository,
)
from src.schemas.approval_schema import (
    ApproveInvoiceRequest,
    ApproveInvoiceResponse,
)


class ApproveInvoiceService:
    DEFAULT_AUDIT_REMARKS = (
        "Invoice approved and finalized for payment processing."
    )

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.approval_repo = ApprovalRepository(
            session,
        )
        self.allocation_finalization_service = (
            AllocationFinalizationService(
                session,
            )
        )
        self.audit_log_service = AuditLogService(
            session,
        )

    async def approve_invoice(
        self,
        invoice_id: UUID,
        request: ApproveInvoiceRequest,
    ) -> ApproveInvoiceResponse:
        snapshot = await self.approval_repo.get_invoice_for_update(
            invoice_id,
        )

        if snapshot is None:
            raise InvoiceNotFoundError(
                str(invoice_id),
            )

        self._validate_invoice_eligibility(
            snapshot.invoice_status,
            snapshot.validation_outcome,
        )

        po_candidate = (
            await self.approval_repo.get_selected_po_candidate(
                invoice_id,
            )
        )

        if po_candidate is None or not po_candidate.po_ids:
            raise InvoiceApprovalValidationError(
                "No selected PO candidate found for invoice.",
            )

        allocation_candidate = (
            await self.approval_repo.get_selected_allocation_candidate(
                invoice_id,
            )
        )

        if (
            allocation_candidate is None
            or not allocation_candidate.items
        ):
            raise InvoiceApprovalValidationError(
                "No selected line allocation candidate found for invoice.",
            )

        await self.allocation_finalization_service.create_final_records(
            invoice_id=invoice_id,
            po_ids=po_candidate.po_ids,
            allocation_items=allocation_candidate.items,
        )
        await self.allocation_finalization_service.finalize_allocations(
            allocation_candidate.items,
        )
        await self.approval_repo.mark_invoice_ready_to_pay(
            invoice_id,
        )

        remarks = (
            request.comments
            if request.comments
            else self.DEFAULT_AUDIT_REMARKS
        )

        await self.audit_log_service.create_audit_log(
            AuditLogCreatePayload(
                invoice_id=invoice_id,
                action="APPROVE_AND_PAY",
                old_status=InvoiceStatus.UNDER_REVIEW.value,
                new_status=InvoiceStatus.READY_TO_PAY.value,
                remarks=remarks,
                performed_by=request.approved_by,
            ),
        )

        return ApproveInvoiceResponse(
            invoice_id=invoice_id,
            invoice_status=InvoiceStatus.READY_TO_PAY.value,
            message=(
                "Invoice approved and finalized for payment processing."
            ),
        )

    @staticmethod
    def _validate_invoice_eligibility(
        invoice_status: InvoiceStatus | None,
        validation_outcome: InvoiceValidationOutcome | None,
    ) -> None:
        if invoice_status == InvoiceStatus.READY_TO_PAY:
            raise InvoiceApprovalConflictError(
                "Invoice has already been approved for payment.",
            )

        if not is_ready_for_approval(
            invoice_status=invoice_status,
            validation_outcome=validation_outcome,
        ):
            raise InvoiceApprovalConflictError(
                "Invoice must have approved validation outcome "
                "and be under human review.",
            )
