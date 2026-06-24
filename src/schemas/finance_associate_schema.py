from __future__ import annotations

from pydantic import BaseModel

from src.schemas.dashboard_schema import (
    DashboardInvoiceListResponse,
)


class FinanceAssociateSummaryResponse(BaseModel):
    ready_for_approval: int
    needs_review: int
    escalated: int
    ready_to_pay: int
    rejected: int


FinanceAssociateInvoiceListResponse = DashboardInvoiceListResponse
