from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, case, exists, func, select, union
from sqlalchemy.orm import aliased

from src.data.models.postgres.audit_log import AuditLog
from src.data.models.postgres.enums import (
    InvoiceStatus,
    POResolutionCandidateType,
    UserRole,
)
from src.data.models.postgres.invoice_po_mapping import InvoicePOMapping
from src.data.models.postgres.invoice_po_resolution_groups import (
    InvoicePOResolutionGroup,
    InvoicePOResolutionGroupItem,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.purchase_orders import PurchaseOrder
from src.data.models.postgres.users import User
from src.data.models.postgres.vendor_master import VendorMaster
from src.core.query.search_filter_builder import (
    ReportFilters,
    SearchFilterBuilder,
)
from src.data.repositories.base_repo import BaseRepository
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)

_RESOLVED_CANDIDATE_TYPES = (
    POResolutionCandidateType.RESOLVED,
    POResolutionCandidateType.RECOVERED,
)

_TOP_VENDORS_LIMIT = 10

_APPROVE_ACTION = "APPROVE_AND_PAY"
_REJECT_ACTION = "REJECT_INVOICE"


@dataclass(frozen=True, slots=True)
class ReportSummaryCounts:
    total_invoices: int
    under_review: int
    ready_to_pay: int
    rejected: int
    escalated: int


@dataclass(frozen=True, slots=True)
class ReportPerformanceMetrics:
    avg_approval_time_hours: float
    avg_rejection_time_hours: float


@dataclass(frozen=True, slots=True)
class VendorSummaryRow:
    vendor_name: str
    invoice_count: int


@dataclass(frozen=True, slots=True)
class AssociateWorkloadRow:
    associate_name: str
    under_review: int
    approved: int
    rejected: int
    escalated: int


@dataclass(frozen=True, slots=True)
class ManagerWorkloadRow:
    manager_name: str
    escalated: int
    claimed_unresolved: int
    approved: int
    rejected: int


class ReportingRepository(BaseRepository):
    async def get_summary_counts(
        self,
        *,
        filters: ReportFilters,
    ) -> ReportSummaryCounts:
        report_filter = SearchFilterBuilder.build_report_filters(
            filters,
        )

        result = await self.execute(
            select(
                func.count().label(
                    "total_invoices",
                ),
                func.count()
                .filter(
                    Invoice.invoice_status
                    == InvoiceStatus.UNDER_REVIEW,
                )
                .label(
                    "under_review",
                ),
                func.count()
                .filter(
                    Invoice.invoice_status
                    == InvoiceStatus.READY_TO_PAY,
                )
                .label(
                    "ready_to_pay",
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
            )
            .select_from(
                Invoice,
            )
            .where(
                report_filter,
            ),
        )
        row = result.one()

        return ReportSummaryCounts(
            total_invoices=int(
                row.total_invoices,
            ),
            under_review=int(
                row.under_review,
            ),
            ready_to_pay=int(
                row.ready_to_pay,
            ),
            rejected=int(
                row.rejected,
            ),
            escalated=int(
                row.escalated,
            ),
        )

    async def get_performance_metrics(
        self,
        *,
        filters: ReportFilters,
    ) -> ReportPerformanceMetrics:
        report_filter = SearchFilterBuilder.build_report_filters(
            filters,
        )

        approval_result = await self.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        AuditLog.created_at - Invoice.created_at,
                    )
                    / 3600.0,
                ),
            )
            .select_from(
                AuditLog,
            )
            .join(
                Invoice,
                AuditLog.invoice_id == Invoice.id,
            )
            .where(
                AuditLog.action == _APPROVE_ACTION,
                report_filter,
            ),
        )
        rejection_result = await self.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        AuditLog.created_at - Invoice.created_at,
                    )
                    / 3600.0,
                ),
            )
            .select_from(
                AuditLog,
            )
            .join(
                Invoice,
                AuditLog.invoice_id == Invoice.id,
            )
            .where(
                AuditLog.action == _REJECT_ACTION,
                report_filter,
            ),
        )

        return ReportPerformanceMetrics(
            avg_approval_time_hours=self._to_hours(
                approval_result.scalar_one(),
            ),
            avg_rejection_time_hours=self._to_hours(
                rejection_result.scalar_one(),
            ),
        )

    async def get_vendor_summary(
        self,
        *,
        filters: ReportFilters,
    ) -> list[VendorSummaryRow]:
        report_filter = SearchFilterBuilder.build_report_filters(
            filters,
        )

        result = await self.execute(
            select(
                func.coalesce(
                    VendorMaster.vendor_name,
                    "Unknown",
                ).label(
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
            .where(
                report_filter,
            )
            .group_by(
                VendorMaster.vendor_name,
            )
            .order_by(
                func.count().desc(),
                func.coalesce(
                    VendorMaster.vendor_name,
                    "Unknown",
                ),
            )
            .limit(
                _TOP_VENDORS_LIMIT,
            ),
        )

        return [
            VendorSummaryRow(
                vendor_name=row.vendor_name,
                invoice_count=int(
                    row.invoice_count,
                ),
            )
            for row in result.all()
        ]

    async def get_associate_workload(
        self,
        *,
        filters: ReportFilters,
    ) -> list[AssociateWorkloadRow]:
        report_filter = SearchFilterBuilder.build_report_filters(
            filters,
        )
        pairs = self._invoice_associate_pairs_subquery()

        associate_conditions: list[ColumnElement[bool]] = [
            User.role == UserRole.FINANCE_ASSOCIATE,
            report_filter,
        ]

        if filters.associate_id is not None:
            associate_conditions.append(
                User.id == filters.associate_id,
            )

        result = await self.execute(
            select(
                User.name.label(
                    "associate_name",
                ),
                func.sum(
                    case(
                        (
                            Invoice.invoice_status
                            == InvoiceStatus.UNDER_REVIEW,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "under_review",
                ),
                func.sum(
                    case(
                        (
                            Invoice.invoice_status
                            == InvoiceStatus.READY_TO_PAY,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "approved",
                ),
                func.sum(
                    case(
                        (
                            Invoice.invoice_status
                            == InvoiceStatus.REJECTED,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "rejected",
                ),
                func.sum(
                    case(
                        (
                            Invoice.invoice_status
                            == InvoiceStatus.ESCALATED,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "escalated",
                ),
            )
            .select_from(
                pairs,
            )
            .join(
                Invoice,
                pairs.c.invoice_id == Invoice.id,
            )
            .join(
                User,
                pairs.c.associate_id == User.id,
            )
            .where(
                and_(
                    *associate_conditions,
                ),
            )
            .group_by(
                User.id,
                User.name,
            )
            .order_by(
                User.name,
            ),
        )

        return [
            AssociateWorkloadRow(
                associate_name=row.associate_name,
                under_review=int(
                    row.under_review or 0,
                ),
                approved=int(
                    row.approved or 0,
                ),
                rejected=int(
                    row.rejected or 0,
                ),
                escalated=int(
                    row.escalated or 0,
                ),
            )
            for row in result.all()
        ]

    async def get_manager_workload(
        self,
        *,
        filters: ReportFilters,
    ) -> list[ManagerWorkloadRow]:
        report_filter = SearchFilterBuilder.build_report_filters(
            filters,
        )
        owned_invoice_ids = select(
            InvoiceOwnershipRepository._owned_invoice_ids_subquery().c.invoice_id,
        )

        escalated_count = (
            select(
                func.count(),
            )
            .select_from(
                Invoice,
            )
            .where(
                Invoice.assigned_manager_id == User.id,
                Invoice.invoice_status == InvoiceStatus.ESCALATED,
                report_filter,
            )
            .correlate(
                User,
            )
            .scalar_subquery()
        )
        claimed_count = (
            select(
                func.count(),
            )
            .select_from(
                Invoice,
            )
            .where(
                Invoice.assigned_manager_id == User.id,
                Invoice.invoice_status == InvoiceStatus.UNDER_REVIEW,
                ~Invoice.id.in_(
                    owned_invoice_ids,
                ),
                report_filter,
            )
            .correlate(
                User,
            )
            .scalar_subquery()
        )
        approved_count = (
            select(
                func.count(),
            )
            .select_from(
                AuditLog,
            )
            .join(
                Invoice,
                AuditLog.invoice_id == Invoice.id,
            )
            .where(
                AuditLog.performed_by == User.id,
                AuditLog.action == _APPROVE_ACTION,
                report_filter,
            )
            .correlate(
                User,
            )
            .scalar_subquery()
        )
        rejected_count = (
            select(
                func.count(),
            )
            .select_from(
                AuditLog,
            )
            .join(
                Invoice,
                AuditLog.invoice_id == Invoice.id,
            )
            .where(
                AuditLog.performed_by == User.id,
                AuditLog.action == _REJECT_ACTION,
                report_filter,
            )
            .correlate(
                User,
            )
            .scalar_subquery()
        )

        manager_conditions: list[ColumnElement[bool]] = [
            User.role == UserRole.FINANCE_MANAGER,
        ]

        if filters.manager_id is not None:
            manager_conditions.append(
                User.id == filters.manager_id,
            )

        result = await self.execute(
            select(
                User.name.label(
                    "manager_name",
                ),
                escalated_count.label(
                    "escalated",
                ),
                claimed_count.label(
                    "claimed_unresolved",
                ),
                approved_count.label(
                    "approved",
                ),
                rejected_count.label(
                    "rejected",
                ),
            )
            .select_from(
                User,
            )
            .where(
                and_(
                    *manager_conditions,
                ),
            )
            .order_by(
                User.name,
            ),
        )

        return [
            ManagerWorkloadRow(
                manager_name=row.manager_name,
                escalated=int(
                    row.escalated or 0,
                ),
                claimed_unresolved=int(
                    row.claimed_unresolved or 0,
                ),
                approved=int(
                    row.approved or 0,
                ),
                rejected=int(
                    row.rejected or 0,
                ),
            )
            for row in result.all()
        ]

    @staticmethod
    def _invoice_associate_pairs_subquery():
        from_mapping = (
            select(
                InvoicePOMapping.invoice_id.label(
                    "invoice_id",
                ),
                PurchaseOrder.uploaded_by.label(
                    "associate_id",
                ),
            )
            .join(
                PurchaseOrder,
                InvoicePOMapping.po_id == PurchaseOrder.id,
            )
            .where(
                PurchaseOrder.uploaded_by.is_not(
                    None,
                ),
            )
        )

        from_selected_group = (
            select(
                InvoicePOResolutionGroup.invoice_id.label(
                    "invoice_id",
                ),
                PurchaseOrder.uploaded_by.label(
                    "associate_id",
                ),
            )
            .join(
                InvoicePOResolutionGroupItem,
                InvoicePOResolutionGroupItem.resolution_group_id
                == InvoicePOResolutionGroup.id,
            )
            .join(
                PurchaseOrder,
                InvoicePOResolutionGroupItem.po_id == PurchaseOrder.id,
            )
            .where(
                PurchaseOrder.uploaded_by.is_not(
                    None,
                ),
                InvoicePOResolutionGroup.is_selected.is_(
                    True,
                ),
            )
        )

        single_resolved_invoice_ids = (
            select(
                InvoicePOResolutionGroup.invoice_id,
            )
            .where(
                InvoicePOResolutionGroup.candidate_type.in_(
                    _RESOLVED_CANDIDATE_TYPES,
                ),
            )
            .group_by(
                InvoicePOResolutionGroup.invoice_id,
            )
            .having(
                func.count(
                    InvoicePOResolutionGroup.id,
                )
                == 1,
            )
        )

        resolution_group = aliased(
            InvoicePOResolutionGroup,
        )
        from_single_resolved_group = (
            select(
                resolution_group.invoice_id.label(
                    "invoice_id",
                ),
                PurchaseOrder.uploaded_by.label(
                    "associate_id",
                ),
            )
            .join(
                InvoicePOResolutionGroupItem,
                InvoicePOResolutionGroupItem.resolution_group_id
                == resolution_group.id,
            )
            .join(
                PurchaseOrder,
                InvoicePOResolutionGroupItem.po_id == PurchaseOrder.id,
            )
            .where(
                PurchaseOrder.uploaded_by.is_not(
                    None,
                ),
                resolution_group.candidate_type.in_(
                    _RESOLVED_CANDIDATE_TYPES,
                ),
                resolution_group.invoice_id.in_(
                    single_resolved_invoice_ids,
                ),
                ~exists(
                    select(
                        1,
                    )
                    .select_from(
                        InvoicePOResolutionGroup,
                    )
                    .where(
                        InvoicePOResolutionGroup.invoice_id
                        == resolution_group.invoice_id,
                        InvoicePOResolutionGroup.is_selected.is_(
                            True,
                        ),
                    ),
                ),
            )
        )

        return union(
            from_mapping,
            from_selected_group,
            from_single_resolved_group,
        ).subquery()

    @staticmethod
    def _to_hours(
        value: float | None,
    ) -> float:
        if value is None:
            return 0.0

        return round(
            float(
                value,
            ),
            1,
        )
