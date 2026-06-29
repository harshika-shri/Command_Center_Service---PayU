from __future__ import annotations

from enum import Enum


class ReportInvoiceStatus(str, Enum):
    READY_FOR_APPROVAL = "ready_for_approval"
    NEEDS_REVIEW = "needs_review"
    READY_TO_PAY = "ready_to_pay"
    OVERDUE = "overdue"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class ReportAssociateViewMode(str, Enum):
    OVERALL = "overall"
    DAYWISE = "daywise"


class ReportValidationOutcome(str, Enum):
    RESOLVED = "resolved"
    RECOVERED = "recovered"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"
    DUPLICATE = "duplicate"


REPORT_VALIDATION_OUTCOME_LABELS: dict[str, str] = {
    ReportValidationOutcome.RESOLVED.value: "Resolved",
    ReportValidationOutcome.RECOVERED.value: "Recovered",
    ReportValidationOutcome.AMBIGUOUS.value: "Ambiguous",
    ReportValidationOutcome.UNRESOLVED.value: "Unresolved",
    ReportValidationOutcome.DUPLICATE.value: "Duplicate",
}


class ReportValidationNode(str, Enum):
    HEADER_VALIDATION = "invoice_header_resolution"
    COMPANY_VALIDATION = "buyer_company_validation"
    VENDOR_VALIDATION = "vendor_resolution"
    DUPLICATE_CHECK = "duplicate_detection"
    PO_MATCHING = "po_resolution"
    LINE_ITEM_MATCHING = "line_item_validation"
    AMOUNT_VALIDATION = "amount_validation"


class ReportIssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReportOverdueFilter(str, Enum):
    ALL = "all"
    YES = "yes"
    NO = "no"


REPORT_INVOICE_STATUS_LABELS: dict[str, str] = {
    ReportInvoiceStatus.READY_FOR_APPROVAL.value: "Ready for Approval",
    ReportInvoiceStatus.NEEDS_REVIEW.value: "Needs Review",
    ReportInvoiceStatus.READY_TO_PAY.value: "Ready to Pay",
    ReportInvoiceStatus.OVERDUE.value: "Overdue",
    ReportInvoiceStatus.REJECTED.value: "Rejected",
    ReportInvoiceStatus.ESCALATED.value: "Escalated",
}

REPORT_VALIDATION_NODE_LABELS: dict[str, str] = {
    ReportValidationNode.HEADER_VALIDATION.value: "Header Validation",
    ReportValidationNode.COMPANY_VALIDATION.value: "Company Validation",
    ReportValidationNode.VENDOR_VALIDATION.value: "Vendor Validation",
    ReportValidationNode.DUPLICATE_CHECK.value: "Duplicate Check",
    ReportValidationNode.PO_MATCHING.value: "PO Matching",
    ReportValidationNode.LINE_ITEM_MATCHING.value: "Line Item Matching",
    ReportValidationNode.AMOUNT_VALIDATION.value: "Amount Validation",
}

REPORT_ISSUE_SEVERITY_LABELS: dict[str, str] = {
    ReportIssueSeverity.CRITICAL.value: "Critical",
    ReportIssueSeverity.HIGH.value: "High",
    ReportIssueSeverity.MEDIUM.value: "Medium",
    ReportIssueSeverity.LOW.value: "Low",
}

INVOICE_REPORT_SORTABLE_COLUMNS: frozenset[str] = frozenset(
    {
        "invoice_number",
        "invoice_date",
        "due_date",
        "invoice_status",
        "validation_outcome",
        "total_amount",
        "vendor_name",
        "company_name",
        "po_number",
        "assigned_finance_associate",
        "created_at",
    },
)

ASSOCIATE_REPORT_SORTABLE_COLUMNS: frozenset[str] = frozenset(
    {
        "report_date",
        "associate_name",
        "total_assigned",
        "approved",
        "rejected",
        "needs_review",
        "ready_for_approval",
        "ready_to_pay",
        "overdue",
        "escalated",
        "resolved_count",
        "recovered_count",
        "approval_rate",
        "rejection_rate",
    },
)

_APPLY_ACTION = "APPROVE_AND_PAY"
_REJECT_ACTION = "REJECT_INVOICE"
_ESCALATE_ACTION = "ESCALATE"
