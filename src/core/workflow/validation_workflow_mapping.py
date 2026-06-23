from __future__ import annotations

from dataclasses import dataclass

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.schemas.validation_event_schema import (
    ValidationEventOutcome,
)


@dataclass(frozen=True, slots=True)
class WorkflowTransition:
    target_status: InvoiceStatus
    target_validation_outcome: InvoiceValidationOutcome
    audit_action: str
    remarks: str


WORKFLOW_TRANSITIONS: dict[
    ValidationEventOutcome,
    WorkflowTransition,
] = {
    ValidationEventOutcome.APPROVED: WorkflowTransition(
        target_status=InvoiceStatus.READY_FOR_APPROVAL,
        target_validation_outcome=InvoiceValidationOutcome.APPROVED,
        audit_action="VALIDATION_COMPLETED",
        remarks="Invoice moved to Ready For Approval bucket",
    ),
    ValidationEventOutcome.PENDING_REVIEW: WorkflowTransition(
        target_status=InvoiceStatus.PARTIALLY_APPROVED,
        target_validation_outcome=InvoiceValidationOutcome.PENDING_REVIEW,
        audit_action="VALIDATION_PENDING_REVIEW",
        remarks="Invoice requires manual review",
    ),
    ValidationEventOutcome.REJECTED: WorkflowTransition(
        target_status=InvoiceStatus.REJECTED,
        target_validation_outcome=InvoiceValidationOutcome.REJECTED,
        audit_action="VALIDATION_REJECTED",
        remarks="Invoice moved to rejected bucket",
    ),
}
