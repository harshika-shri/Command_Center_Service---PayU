from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from src.data.models.postgres.enums import InvoiceStatus
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository


@dataclass(frozen=True, slots=True)
class DashboardSummaryCounts:
    ready_for_approval: int
    partially_approved: int
    rejected: int
    escalated: int
    total: int


@dataclass(frozen=True, slots=True)
class DashboardInvoiceRow:
    invoice_id: UUID
    invoice_number: str | None
    invoice_date: date | None
    vendor_name: str | None
    total_amount: Decimal | None
    validation_outcome: str | None
    invoice_status: str | None
    rejection_reason: str | None
    escalated_to: UUID | None
    created_at: datetime


class DashboardRepository(BaseRepository):
    async def get_summary_counts(self) -> DashboardSummaryCounts:
        result = await self.execute(
            select(
                func.count()
                .filter(
                    Invoice.invoice_status == InvoiceStatus.READY_FOR_APPROVAL,
                )
                .label(
                    "ready_for_approval",
                ),
                func.count()
                .filter(
                    Invoice.invoice_status == InvoiceStatus.PARTIALLY_APPROVED,
                )
                .label(
                    "partially_approved",
                ),
                func.count()
                .filter(
                    Invoice.invoice_status == InvoiceStatus.REJECTED,
                )
                .label(
                    "rejected",
                ),
                func.count()
                .filter(
                    Invoice.invoice_status == InvoiceStatus.ESCALATED,
                )
                .label(
                    "escalated",
                ),
            ).select_from(
                Invoice,
            ),
        )
        row = result.one()

        return DashboardSummaryCounts(
            ready_for_approval=row.ready_for_approval,
            partially_approved=row.partially_approved,
            rejected=row.rejected,
            escalated=row.escalated,
            total=(
                row.ready_for_approval
                + row.partially_approved
                + row.rejected
                + row.escalated
            ),
        )

    async def list_invoices_by_status(
        self,
        *,
        invoice_status: InvoiceStatus,
        offset: int,
        limit: int,
    ) -> tuple[list[DashboardInvoiceRow], int]:
        base_query = (
            select(
                Invoice.id,
                Invoice.invoice_number,
                Invoice.invoice_date,
                VendorMaster.vendor_name,
                Invoice.total_amount,
                Invoice.validation_outcome,
                Invoice.invoice_status,
                Invoice.rejection_reason,
                Invoice.escalated_to,
                Invoice.created_at,
            )
            .select_from(
                Invoice,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .where(
                Invoice.invoice_status == invoice_status,
            )
        )

        count_result = await self.execute(
            select(
                func.count(),
            )
            .select_from(
                Invoice,
            )
            .where(
                Invoice.invoice_status == invoice_status,
            ),
        )
        total_records = int(
            count_result.scalar_one(),
        )

        list_result = await self.execute(
            base_query.order_by(
                Invoice.created_at.desc(),
            )
            .offset(
                offset,
            )
            .limit(
                limit,
            ),
        )

        items = [
            DashboardInvoiceRow(
                invoice_id=row.id,
                invoice_number=row.invoice_number,
                invoice_date=row.invoice_date,
                vendor_name=row.vendor_name,
                total_amount=row.total_amount,
                validation_outcome=(
                    row.validation_outcome.value
                    if row.validation_outcome is not None
                    else None
                ),
                invoice_status=(
                    row.invoice_status.value if row.invoice_status is not None else None
                ),
                rejection_reason=row.rejection_reason,
                escalated_to=row.escalated_to,
                created_at=row.created_at,
            )
            for row in list_result.all()
        ]

        return items, total_records
