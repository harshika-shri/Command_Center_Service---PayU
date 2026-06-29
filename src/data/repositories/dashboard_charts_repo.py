from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select

from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
    dashboard_bucket_filter,
)
from src.data.models.postgres.audit_log import AuditLog
from src.data.models.postgres.enums import (
    UserRole,
    ValidationIssueStatus,
)
from src.data.models.postgres.invoice_extracted_vendor import InvoiceExtractedVendor
from src.data.models.postgres.invoice_validation_issues import (
    InvoiceValidationIssue,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.users import User
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)

_STATUS_BUCKETS: tuple[tuple[DashboardBucket, str], ...] = (
    (DashboardBucket.READY_FOR_APPROVAL, "Ready for Approval"),
    (DashboardBucket.NEEDS_REVIEW, "Needs Review"),
    (DashboardBucket.READY_TO_PAY, "Ready to Pay"),
    (DashboardBucket.OVERDUE, "Overdue"),
    (DashboardBucket.REJECTED, "Rejected"),
)

_VALIDATION_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Header Validation", ("invoice_header_resolution",)),
    ("Company Validation", ("buyer_company_validation",)),
    ("Vendor Validation", ("vendor_resolution",)),
    ("Duplicate Check", ("duplicate_detection",)),
    ("PO Matching", ("po_resolution",)),
    ("Line Item Matching", ("line_item_validation",)),
    ("Amount Validation", ("amount_validation",)),
)

_UNRESOLVED_ISSUE_STATUSES = (
    ValidationIssueStatus.OPEN,
    ValidationIssueStatus.PENDING_REVIEW,
)

_PROCESSING_ACTIONS = (
    "APPROVE_AND_PAY",
    "REJECT_INVOICE",
    "ESCALATE",
)

_PENDING_WORK_BUCKETS = (
    DashboardBucket.READY_FOR_APPROVAL,
    DashboardBucket.NEEDS_REVIEW,
    DashboardBucket.OVERDUE,
)


class DashboardChartsRepository(BaseRepository):
    async def get_status_distribution(
        self,
        *,
        associate_id: UUID | None = None,
    ) -> tuple[list[str], list[int]]:
        labels: list[str] = []
        values: list[int] = []

        ownership_filter = None
        if associate_id is not None:
            ownership_filter = InvoiceOwnershipRepository.associate_ownership_filter(
                associate_id,
            )

        for bucket, label in _STATUS_BUCKETS:
            bucket_filter = dashboard_bucket_filter(bucket)
            query = select(func.count()).select_from(Invoice).where(bucket_filter)

            if ownership_filter is not None:
                query = query.where(ownership_filter)

            result = await self.execute(query)
            labels.append(label)
            values.append(int(result.scalar_one()))

        return labels, values

    async def get_validation_breakdown(
        self,
        *,
        associate_id: UUID | None = None,
    ) -> tuple[list[str], list[int]]:
        labels: list[str] = []
        values: list[int] = []

        ownership_filter = None
        if associate_id is not None:
            ownership_filter = InvoiceOwnershipRepository.associate_ownership_filter(
                associate_id,
            )

        for label, stages in _VALIDATION_CATEGORIES:
            query = (
                select(
                    func.count(
                        func.distinct(
                            InvoiceValidationIssue.invoice_id,
                        ),
                    ),
                )
                .select_from(InvoiceValidationIssue)
                .join(
                    Invoice,
                    InvoiceValidationIssue.invoice_id == Invoice.id,
                )
                .where(
                    InvoiceValidationIssue.check_stage.in_(stages),
                    InvoiceValidationIssue.status.in_(
                        _UNRESOLVED_ISSUE_STATUSES,
                    ),
                )
            )

            if ownership_filter is not None:
                query = query.where(ownership_filter)

            result = await self.execute(query)
            labels.append(label)
            values.append(int(result.scalar_one()))

        return labels, values

    async def get_processing_trend(
        self,
        associate_id: UUID,
        *,
        days: int = 7,
    ) -> tuple[list[str], list[int]]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        result = await self.execute(
            select(
                func.date(
                    AuditLog.created_at,
                ).label("activity_date"),
                func.count().label("processed_count"),
            )
            .where(
                AuditLog.performed_by == associate_id,
                AuditLog.action.in_(
                    _PROCESSING_ACTIONS,
                ),
                func.date(
                    AuditLog.created_at,
                )
                >= start_date,
                func.date(
                    AuditLog.created_at,
                )
                <= end_date,
            )
            .group_by(
                func.date(
                    AuditLog.created_at,
                ),
            )
            .order_by(
                func.date(
                    AuditLog.created_at,
                ),
            ),
        )

        counts_by_date = {
            row.activity_date: int(row.processed_count)
            for row in result.all()
        }

        labels: list[str] = []
        values: list[int] = []

        current = start_date
        while current <= end_date:
            labels.append(current.strftime("%b %d"))
            values.append(counts_by_date.get(current, 0))
            current += timedelta(days=1)

        return labels, values

    async def get_team_performance(
        self,
    ) -> tuple[list[str], list[int]]:
        result = await self.execute(
            select(
                User.name,
                func.count(
                    func.distinct(
                        AuditLog.invoice_id,
                    ),
                ).label("processed_count"),
            )
            .select_from(AuditLog)
            .join(
                User,
                AuditLog.performed_by == User.id,
            )
            .where(
                User.role == UserRole.FINANCE_ASSOCIATE,
                AuditLog.action.in_(
                    _PROCESSING_ACTIONS,
                ),
            )
            .group_by(
                User.id,
                User.name,
            )
            .order_by(
                func.count(
                    func.distinct(
                        AuditLog.invoice_id,
                    ),
                ).desc(),
                User.name.asc(),
            ),
        )

        rows = result.all()
        labels = [row.name for row in rows]
        values = [int(row.processed_count) for row in rows]
        return labels, values

    async def get_pending_work_by_vendor(
        self,
    ) -> tuple[list[str], list[int]]:
        pending_filter = or_(
            *(
                dashboard_bucket_filter(bucket)
                for bucket in _PENDING_WORK_BUCKETS
            ),
        )

        vendor_name = func.coalesce(
            VendorMaster.vendor_name,
            InvoiceExtractedVendor.vendor_name,
            "Unknown Vendor",
        ).label("vendor_name")

        result = await self.execute(
            select(
                vendor_name,
                func.count(Invoice.id).label("pending_count"),
            )
            .select_from(Invoice)
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .outerjoin(
                InvoiceExtractedVendor,
                Invoice.id == InvoiceExtractedVendor.invoice_id,
            )
            .where(
                pending_filter,
            )
            .group_by(
                vendor_name,
            )
            .order_by(
                func.count(Invoice.id).desc(),
                vendor_name.asc(),
            ),
        )

        rows = result.all()
        labels = [row.vendor_name for row in rows]
        values = [int(row.pending_count) for row in rows]
        return labels, values
