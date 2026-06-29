from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import Date, cast, func, literal, or_, select

from src.constants.report_constants import REPORT_VALIDATION_NODE_LABELS
from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
    dashboard_bucket_filter,
)
from src.data.models.postgres.audit_log import AuditLog
from src.data.models.postgres.enums import (
    InvoiceStatus,
    UserRole,
    ValidationIssueStatus,
)
from src.data.models.postgres.invoice_extracted_vendor import (
    InvoiceExtractedVendor,
)
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

_PROCESSING_ACTIONS = (
    "APPROVE_AND_PAY",
    "REJECT_INVOICE",
    "ESCALATE",
)

_UNRESOLVED_ISSUE_STATUSES = (
    ValidationIssueStatus.OPEN,
    ValidationIssueStatus.PENDING_REVIEW,
)

_ASSOCIATE_STATUS_BUCKETS: list[tuple[str, DashboardBucket | None]] = [
    ("Ready for Approval", DashboardBucket.READY_FOR_APPROVAL),
    ("Needs Review", DashboardBucket.NEEDS_REVIEW),
    ("Escalated", DashboardBucket.ESCALATED),
    ("Ready to Pay", DashboardBucket.READY_TO_PAY),
    ("Rejected", DashboardBucket.REJECTED),
]

_MANAGER_STATUS_BUCKETS: list[tuple[str, DashboardBucket | None]] = [
    ("Ready for Approval", DashboardBucket.READY_FOR_APPROVAL),
    ("Needs Review", DashboardBucket.NEEDS_REVIEW),
    ("Escalated", DashboardBucket.ESCALATED),
    ("Ready to Pay", DashboardBucket.READY_TO_PAY),
    ("Rejected", DashboardBucket.REJECTED),
]

_PENDING_VENDOR_BUCKETS = (
    DashboardBucket.READY_FOR_APPROVAL,
    DashboardBucket.NEEDS_REVIEW,
    DashboardBucket.ESCALATED,
)

_TOP_VENDORS_LIMIT = 10
_TREND_DAYS = 7


class DashboardChartsRepository(BaseRepository):
    async def get_associate_status_distribution(
        self,
        associate_id: UUID,
    ) -> tuple[list[str], list[int]]:
        labels: list[str] = []
        values: list[int] = []

        ownership_filter = (
            InvoiceOwnershipRepository.associate_ownership_filter(
                associate_id,
            )
        )

        for label, bucket in _ASSOCIATE_STATUS_BUCKETS:
            if bucket is None:
                continue

            count = await self._count_invoices(
                dashboard_bucket_filter(
                    bucket,
                ),
                ownership_filter,
            )
            labels.append(
                label,
            )
            values.append(
                count,
            )

        overdue_count = await self._count_invoices(
            Invoice.invoice_status == InvoiceStatus.OVERDUE,
            ownership_filter,
        )
        labels.append(
            "Overdue",
        )
        values.append(
            overdue_count,
        )

        return labels, values

    async def get_manager_status_distribution(
        self,
    ) -> tuple[list[str], list[int]]:
        labels: list[str] = []
        values: list[int] = []

        for label, bucket in _MANAGER_STATUS_BUCKETS:
            if bucket is None:
                continue

            count = await self._count_invoices(
                dashboard_bucket_filter(
                    bucket,
                ),
            )
            labels.append(
                label,
            )
            values.append(
                count,
            )

        overdue_count = await self._count_invoices(
            Invoice.invoice_status == InvoiceStatus.OVERDUE,
        )
        labels.append(
            "Overdue",
        )
        values.append(
            overdue_count,
        )

        return labels, values

    async def get_associate_validation_breakdown(
        self,
        associate_id: UUID,
    ) -> tuple[list[str], list[int]]:
        ownership_filter = (
            InvoiceOwnershipRepository.associate_ownership_filter(
                associate_id,
            )
        )

        result = await self.execute(
            select(
                InvoiceValidationIssue.check_stage,
                func.count().label(
                    "issue_count",
                ),
            )
            .select_from(
                InvoiceValidationIssue,
            )
            .join(
                Invoice,
                InvoiceValidationIssue.invoice_id == Invoice.id,
            )
            .where(
                InvoiceValidationIssue.status.in_(
                    _UNRESOLVED_ISSUE_STATUSES,
                ),
                ownership_filter,
            )
            .group_by(
                InvoiceValidationIssue.check_stage,
            )
            .order_by(
                func.count().desc(),
            ),
        )

        labels: list[str] = []
        values: list[int] = []

        for row in result.all():
            labels.append(
                REPORT_VALIDATION_NODE_LABELS.get(
                    row.check_stage,
                    row.check_stage.replace(
                        "_",
                        " ",
                    ).title(),
                ),
            )
            values.append(
                int(
                    row.issue_count,
                ),
            )

        return labels, values

    async def get_manager_validation_breakdown(
        self,
    ) -> tuple[list[str], list[int]]:
        result = await self.execute(
            select(
                InvoiceValidationIssue.check_stage,
                func.count().label(
                    "issue_count",
                ),
            )
            .select_from(
                InvoiceValidationIssue,
            )
            .where(
                InvoiceValidationIssue.status.in_(
                    _UNRESOLVED_ISSUE_STATUSES,
                ),
            )
            .group_by(
                InvoiceValidationIssue.check_stage,
            )
            .order_by(
                func.count().desc(),
            ),
        )

        labels: list[str] = []
        values: list[int] = []

        for row in result.all():
            labels.append(
                REPORT_VALIDATION_NODE_LABELS.get(
                    row.check_stage,
                    row.check_stage.replace(
                        "_",
                        " ",
                    ).title(),
                ),
            )
            values.append(
                int(
                    row.issue_count,
                ),
            )

        return labels, values

    async def get_associate_processing_trend(
        self,
        associate_id: UUID,
    ) -> tuple[list[str], list[int]]:
        start_date = date.today() - timedelta(
            days=_TREND_DAYS - 1,
        )
        day_labels = [
            (start_date + timedelta(days=offset)).isoformat()
            for offset in range(
                _TREND_DAYS,
            )
        ]
        counts_by_day = dict.fromkeys(
            day_labels,
            0,
        )

        result = await self.execute(
            select(
                cast(
                    AuditLog.created_at,
                    Date,
                ).label(
                    "activity_date",
                ),
                func.count().label(
                    "activity_count",
                ),
            )
            .where(
                AuditLog.performed_by == associate_id,
                AuditLog.action.in_(
                    _PROCESSING_ACTIONS,
                ),
                cast(
                    AuditLog.created_at,
                    Date,
                )
                >= start_date,
            )
            .group_by(
                cast(
                    AuditLog.created_at,
                    Date,
                ),
            ),
        )

        for row in result.all():
            key = row.activity_date.isoformat()
            if key in counts_by_day:
                counts_by_day[key] = int(
                    row.activity_count,
                )

        return day_labels, [
            counts_by_day[label]
            for label in day_labels
        ]

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
                ).label(
                    "processed_count",
                ),
            )
            .select_from(
                AuditLog,
            )
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
                User.name,
            ),
        )

        labels: list[str] = []
        values: list[int] = []

        for row in result.all():
            labels.append(
                row.name,
            )
            values.append(
                int(
                    row.processed_count or 0,
                ),
            )

        return labels, values

    async def get_pending_work_by_vendor(
        self,
    ) -> tuple[list[str], list[int]]:
        pending_filter = or_(
            *[
                dashboard_bucket_filter(
                    bucket,
                )
                for bucket in _PENDING_VENDOR_BUCKETS
            ],
            Invoice.invoice_status == InvoiceStatus.OVERDUE,
        )

        vendor_name_expr = func.coalesce(
            VendorMaster.vendor_name,
            InvoiceExtractedVendor.vendor_name,
            literal(
                "Unknown",
            ),
        )

        result = await self.execute(
            select(
                vendor_name_expr.label(
                    "vendor_name",
                ),
                func.count().label(
                    "invoice_count",
                ),
            )
            .select_from(
                Invoice,
            )
            .outerjoin(
                VendorMaster,
                Invoice.vendor_id == VendorMaster.id,
            )
            .outerjoin(
                InvoiceExtractedVendor,
                InvoiceExtractedVendor.invoice_id == Invoice.id,
            )
            .where(
                pending_filter,
            )
            .group_by(
                vendor_name_expr,
            )
            .order_by(
                func.count().desc(),
            )
            .limit(
                _TOP_VENDORS_LIMIT,
            ),
        )

        labels: list[str] = []
        values: list[int] = []

        for row in result.all():
            labels.append(
                row.vendor_name,
            )
            values.append(
                int(
                    row.invoice_count,
                ),
            )

        return labels, values

    async def _count_invoices(
        self,
        *filters,
    ) -> int:
        from sqlalchemy import and_

        conditions = [condition for condition in filters if condition is not None]
        where_clause = and_(
            *conditions,
        ) if conditions else None

        query = select(
            func.count(),
        ).select_from(
            Invoice,
        )

        if where_clause is not None:
            query = query.where(
                where_clause,
            )

        result = await self.execute(
            query,
        )

        return int(
            result.scalar_one(),
        )
