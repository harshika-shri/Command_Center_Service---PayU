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
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.APPROVED,
        audit_action="VALIDATION_COMPLETED",
        remarks=(
            "Validation completed with approved outcome; "
            "invoice moved to human review"
        ),
    ),
    ValidationEventOutcome.PENDING_REVIEW: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.PENDING_REVIEW,
        audit_action="VALIDATION_PENDING_REVIEW",
        remarks=(
            "Validation completed with pending review outcome; "
            "invoice moved to human review"
        ),
    ),
    ValidationEventOutcome.REJECTED: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.REJECTED,
        audit_action="VALIDATION_REJECTED",
        remarks=(
            "Validation completed with rejected outcome; "
            "invoice moved to human review"
        ),
    ),
}
