from __future__ import annotations

from pydantic import BaseModel

from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardSummaryResponse,
)
from src.schemas.invoice_review_schema import (
    InvoiceReviewResponse,
)


class FinanceAssociateSummaryResponse(BaseModel):
    ready_for_approval: int
    needs_review: int
    escalated: int
    ready_to_pay: int
    rejected: int


class FinanceAssociateReviewResponse(BaseModel):
    review: InvoiceReviewResponse
    can_take_action: bool


FinanceAssociateInvoiceListResponse = DashboardInvoiceListResponse
FinanceAssociateDashboardSummaryResponse = DashboardSummaryResponse
