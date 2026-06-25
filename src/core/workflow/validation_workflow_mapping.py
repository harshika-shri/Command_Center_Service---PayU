from __future__ import annotations

from dataclasses import dataclass

from src.constants.redis_stream_constants import (
    VALIDATION_EVENT_TYPE_COMPLETED,
    VALIDATION_EVENT_TYPE_PENDING_REVIEW,
    VALIDATION_EVENT_TYPE_REJECTED,
)
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)


@dataclass(frozen=True, slots=True)
class WorkflowTransition:
    target_status: InvoiceStatus
    target_validation_outcome: InvoiceValidationOutcome
    audit_action: str
    remarks: str


WORKFLOW_TRANSITIONS: dict[
    str,
    WorkflowTransition,
] = {
    VALIDATION_EVENT_TYPE_COMPLETED: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.APPROVED,
        audit_action="VALIDATION_COMPLETED",
        remarks=(
            "Validation completed with approved outcome; "
            "invoice moved to human review"
        ),
    ),
    VALIDATION_EVENT_TYPE_PENDING_REVIEW: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.PENDING_REVIEW,
        audit_action="VALIDATION_PENDING_REVIEW",
        remarks=(
            "Validation completed with pending review outcome; "
            "invoice moved to human review"
        ),
    ),
    VALIDATION_EVENT_TYPE_REJECTED: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.REJECTED,
        audit_action="VALIDATION_REJECTED",
        remarks=(
            "Validation completed with rejected outcome; "
            "invoice moved to human review"
        ),
    ),
}
