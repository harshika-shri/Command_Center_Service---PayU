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
    ValidationEventOutcome.RESOLVED: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.RESOLVED,
        audit_action="VALIDATION_RESOLVED",
        remarks=(
            "Validation completed with resolved outcome; "
            "invoice moved to human review"
        ),
    ),
    ValidationEventOutcome.RECOVERED: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.RECOVERED,
        audit_action="VALIDATION_RECOVERED",
        remarks=(
            "Validation completed with recovered outcome; "
            "invoice moved to human review"
        ),
    ),
    ValidationEventOutcome.AMBIGUOUS: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.AMBIGUOUS,
        audit_action="VALIDATION_AMBIGUOUS",
        remarks=(
            "Validation completed with ambiguous outcome; "
            "invoice moved to human review"
        ),
    ),
    ValidationEventOutcome.UNRESOLVED: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.UNRESOLVED,
        audit_action="VALIDATION_UNRESOLVED",
        remarks=(
            "Validation completed with unresolved outcome; "
            "invoice moved to human review"
        ),
    ),
    ValidationEventOutcome.DUPLICATE: WorkflowTransition(
        target_status=InvoiceStatus.UNDER_REVIEW,
        target_validation_outcome=InvoiceValidationOutcome.DUPLICATE,
        audit_action="VALIDATION_DUPLICATE",
        remarks=(
            "Validation completed with duplicate outcome; "
            "invoice moved to human review"
        ),
    ),
}
