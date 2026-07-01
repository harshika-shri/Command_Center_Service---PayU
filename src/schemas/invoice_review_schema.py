from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceVendorSummary(BaseModel):
    vendor_name: str | None = None
    vendor_code: str | None = None
    gstin: str | None = None
    email: str | None = None


class InvoiceCompanySummary(BaseModel):
    company_name: str | None = None
    company_code: str | None = None
    gstin: str | None = None


class InvoiceWorkflowState(BaseModel):
    validation_outcome: str | None = Field(
        default=None,
        description="System validation result from Validation Service.",
    )
    invoice_status: str | None = Field(
        default=None,
        description="Human workflow status managed by Command Center.",
    )


class InvoiceHeaderResponse(BaseModel):
    invoice_id: UUID
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None
    vendor: InvoiceVendorSummary | None = None
    company: InvoiceCompanySummary | None = None
    subtotal_amount: float | None
    tax_amount: float | None
    total_amount: float | None
    payment_terms: str | None
    notes: str | None
    invoice_status: str | None
    validation_outcome: str | None
    received_email: str | None
    created_at: datetime
    updated_at: datetime


class InvoiceEmailDetails(BaseModel):
    received_from: str | None = None
    subject: str | None = None
    body_text: str | None = None
    attachment_filename: str | None = None


class ExtractedVendorDetails(BaseModel):
    vendor_name: str | None = None
    vendor_gstin: str | None = None
    vendor_address: str | None = None
    vendor_email: str | None = None
    vendor_phone: str | None = None
    bank_account_number: str | None = None
    bank_name: str | None = None
    ifsc_code: str | None = None
    account_holder_name: str | None = None


class InvoiceLineItemDetails(BaseModel):
    id: UUID
    line_number: int
    item_code: str | None
    item_description: str | None
    uom: str | None
    quantity_billed: float
    unit_price: float
    discount_amount: float | None
    tax_details: dict[str, Any] | None
    hsn_sac_code: str | None
    line_total: float
    is_item_code_matched: bool | None
    is_unauthorized_extra_item: bool | None
    is_hsn_matched: bool | None
    is_line_total_correct: bool | None
    is_unit_price_matched: bool | None
    is_quantity_valid: bool | None
    is_uom_matched: bool | None
    is_tax_correct: bool | None
    created_at: datetime


class ConfidenceScoreDetails(BaseModel):
    id: UUID
    field_name: str
    extracted_value: str | None
    confidence_score: float
    is_flagged: bool
    created_at: datetime


class InvoiceExtractionResponse(BaseModel):
    email_details: InvoiceEmailDetails | None = None
    vendor_details: ExtractedVendorDetails | None = None
    line_items: list[InvoiceLineItemDetails] = Field(
        default_factory=list,
    )
    confidence_scores: list[ConfidenceScoreDetails] = Field(
        default_factory=list,
    )


class ValidationIssueDetails(BaseModel):
    id: UUID
    check_stage: str
    check_name: str
    field_name: str | None
    issue_type: str
    expected_value: str | None
    actual_value: str | None
    description: str
    status: str
    metadata: dict[str, Any] | None = None


class ReviewSummaryDetails(BaseModel):
    decision: str
    executive_summary: str
    system_recoveries_json: list[Any]
    open_issues_json: list[Any]
    vendor_clarifications_json: list[Any]
    validation_steps_json: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime


class InvoiceValidationResponse(BaseModel):
    validation_outcome: str | None
    clarification_sent: bool = False
    issues: list[ValidationIssueDetails] = Field(
        default_factory=list,
    )
    review_summary: ReviewSummaryDetails | None = None


class POCandidatePurchaseOrderDetails(BaseModel):
    po_id: UUID
    po_number: str
    status: str
    total_amount: float | None
    consumed_amount: float
    po_date: date
    vendor_name: str | None


class POCandidateGroupDetails(BaseModel):
    id: UUID
    candidate_type: str
    confidence_score: float | None
    is_selected: bool
    purchase_orders: list[POCandidatePurchaseOrderDetails] = Field(
        default_factory=list,
    )


class POCandidateResponse(BaseModel):
    candidate_groups: list[POCandidateGroupDetails] = Field(
        default_factory=list,
    )


class LineAllocationInvoiceLineDetails(BaseModel):
    item_code: str | None
    item_description: str | None
    quantity_billed: float
    line_total: float


class LineAllocationPOLineDetails(BaseModel):
    item_code: str | None
    item_description: str
    quantity_ordered: float
    consumed_quantity: float
    line_total: float


class LineAllocationCandidateItemDetails(BaseModel):
    id: UUID
    invoice_line_item_id: UUID
    po_line_item_id: UUID
    allocated_quantity: float
    allocated_amount: float
    candidate_type: str
    invoice_line_item: LineAllocationInvoiceLineDetails
    po_line_item: LineAllocationPOLineDetails


class LineAllocationCandidateGroupDetails(BaseModel):
    id: UUID
    candidate_type: str
    confidence_score: float | None
    is_selected: bool
    items: list[LineAllocationCandidateItemDetails] = Field(
        default_factory=list,
    )


class LineAllocationCandidateResponse(BaseModel):
    candidate_groups: list[LineAllocationCandidateGroupDetails] = Field(
        default_factory=list,
    )


class InvoiceReviewResponse(BaseModel):
    workflow: InvoiceWorkflowState
    header: InvoiceHeaderResponse
    extraction: InvoiceExtractionResponse
    validation: InvoiceValidationResponse
    po_candidates: POCandidateResponse
    line_allocation_candidates: LineAllocationCandidateResponse
