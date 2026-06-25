from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
)
from src.schemas.invoice_review_schema import (
    InvoiceReviewResponse,
)


class FinanceManagerSummaryResponse(BaseModel):
    my_escalated: int
    unassigned_queue: int
    my_claimed_unresolved: int
    rejected: int


class InvoiceOwnershipDetails(BaseModel):
    associate_owner_id: UUID | None = None
    associate_owner_name: str | None = None
    associate_owner_email: str | None = None
    assigned_manager_id: UUID | None = None
    assigned_manager_name: str | None = None
    assigned_manager_email: str | None = None
    escalated_by_id: UUID | None = None
    escalated_by_name: str | None = None
    escalated_by_email: str | None = None
    assigned_at: datetime | None = None


class DisputeHistoryItem(BaseModel):
    dispute_id: UUID
    reason_category: str
    status: str
    description: str | None = None
    raised_by_id: UUID
    raised_by_name: str | None = None
    created_at: datetime


class CommunicationTimelineItem(BaseModel):
    communication_id: UUID
    dispute_id: UUID
    communication_type: str
    reason_category: str
    subject: str
    body: str
    recipient_email: str
    status: str
    sent_at: datetime | None = None
    sent_by_id: UUID | None = None
    sent_by_name: str | None = None
    created_at: datetime


class FinanceManagerReviewResponse(BaseModel):
    review: InvoiceReviewResponse
    ownership: InvoiceOwnershipDetails
    disputes: list[DisputeHistoryItem]
    communication_timeline: list[CommunicationTimelineItem]
    can_take_action: bool
    can_take_ownership: bool


FinanceManagerInvoiceListResponse = DashboardInvoiceListResponse
