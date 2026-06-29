from __future__ import annotations

from sqlalchemy import ColumnElement, case

from src.constants.report_constants import ReportIssueSeverity
from src.data.models.postgres.enums import (
    IssueType,
    ValidationIssueStatus,
)
from src.data.models.postgres.invoice_validation_issues import (
    InvoiceValidationIssue,
)


def issue_severity_expression() -> ColumnElement[str]:
    return case(
        (
            InvoiceValidationIssue.issue_type.in_(
                (
                    IssueType.INVALID,
                    IssueType.MISSING,
                    IssueType.MISMATCH,
                    IssueType.DUPLICATE,
                    IssueType.AMBIGUOUS,
                ),
            ),
            ReportIssueSeverity.CRITICAL.value,
        ),
        (
            InvoiceValidationIssue.status.in_(
                (
                    ValidationIssueStatus.OPEN,
                    ValidationIssueStatus.PENDING_REVIEW,
                ),
            ),
            ReportIssueSeverity.CRITICAL.value,
        ),
        (
            InvoiceValidationIssue.issue_type == IssueType.LOW_CONFIDENCE,
            ReportIssueSeverity.HIGH.value,
        ),
        (
            InvoiceValidationIssue.status.in_(
                (
                    ValidationIssueStatus.RESOLVED,
                    ValidationIssueStatus.WAIVED,
                ),
            ),
            ReportIssueSeverity.LOW.value,
        ),
        else_=ReportIssueSeverity.MEDIUM.value,
    ).label(
        "issue_severity",
    )


def severity_rank_expression(
    severity_column: ColumnElement[str],
) -> ColumnElement[int]:
    return case(
        (severity_column == ReportIssueSeverity.CRITICAL.value, 4),
        (severity_column == ReportIssueSeverity.HIGH.value, 3),
        (severity_column == ReportIssueSeverity.MEDIUM.value, 2),
        (severity_column == ReportIssueSeverity.LOW.value, 1),
        else_=0,
    )
