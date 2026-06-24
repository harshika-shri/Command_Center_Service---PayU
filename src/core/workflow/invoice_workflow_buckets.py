from __future__ import annotations

from enum import Enum

from sqlalchemy import ColumnElement, and_

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.models.postgres.invoices import Invoice


class DashboardBucket(str, Enum):
    READY_FOR_APPROVAL = "ready_for_approval"
    NEEDS_REVIEW = "needs_review"
    ESCALATED = "escalated"
    READY_TO_PAY = "ready_to_pay"
    REJECTED = "rejected"


_NEEDS_REVIEW_OUTCOMES = (
    InvoiceValidationOutcome.PENDING_REVIEW,
    InvoiceValidationOutcome.REJECTED,
)


def dashboard_bucket_filter(
    bucket: DashboardBucket,
) -> ColumnElement[bool]:
    if bucket == DashboardBucket.READY_FOR_APPROVAL:
        return and_(
            Invoice.invoice_status == InvoiceStatus.UNDER_REVIEW,
            Invoice.validation_outcome == InvoiceValidationOutcome.APPROVED,
        )

    if bucket == DashboardBucket.NEEDS_REVIEW:
        return and_(
            Invoice.invoice_status == InvoiceStatus.UNDER_REVIEW,
            Invoice.validation_outcome.in_(
                _NEEDS_REVIEW_OUTCOMES,
            ),
        )

    if bucket == DashboardBucket.ESCALATED:
        return Invoice.invoice_status == InvoiceStatus.ESCALATED

    if bucket == DashboardBucket.READY_TO_PAY:
        return Invoice.invoice_status == InvoiceStatus.READY_TO_PAY

    if bucket == DashboardBucket.REJECTED:
        return Invoice.invoice_status == InvoiceStatus.REJECTED

    raise ValueError(
        f"Unsupported dashboard bucket: {bucket}",
    )


def is_ready_for_approval(
    *,
    invoice_status: InvoiceStatus | None,
    validation_outcome: InvoiceValidationOutcome | None,
) -> bool:
    return (
        invoice_status == InvoiceStatus.UNDER_REVIEW
        and validation_outcome == InvoiceValidationOutcome.APPROVED
    )


def is_eligible_for_escalation(
    invoice_status: InvoiceStatus | None,
) -> bool:
    return invoice_status == InvoiceStatus.UNDER_REVIEW


def is_eligible_for_clarification(
    *,
    invoice_status: InvoiceStatus | None,
    validation_outcome: InvoiceValidationOutcome | None,
) -> bool:
    _ = validation_outcome
    return invoice_status in (
        InvoiceStatus.UNDER_REVIEW,
        InvoiceStatus.ESCALATED,
    )


def is_eligible_for_business_rejection(
    invoice_status: InvoiceStatus | None,
) -> bool:
    return invoice_status in (
        InvoiceStatus.UNDER_REVIEW,
        InvoiceStatus.ESCALATED,
    )


def is_rejected_for_vendor_communication(
    invoice_status: InvoiceStatus | None,
) -> bool:
    return invoice_status == InvoiceStatus.REJECTED
