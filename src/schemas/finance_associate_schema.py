from __future__ import annotations

from pydantic import BaseModel

from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
    DashboardSummaryResponse,
)
from src.schemas.invoice_review_schema import (
    InvoiceReviewResponse,
)


class FinanceAssociateReviewResponse(BaseModel):
    review: InvoiceReviewResponse
    can_take_action: bool


FinanceAssociateSummaryResponse = DashboardSummaryResponse
FinanceAssociateInvoiceListResponse = DashboardInvoiceListResponse
