from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    ColumnElement,
    Date,
    String,
    and_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    true,
    union,
)
from sqlalchemy.orm import aliased

from src.constants.report_constants import (
    ReportAssociateViewMode,
    ReportInvoiceStatus,
    ReportIssueSeverity,
    ReportOverdueFilter,
    _APPLY_ACTION,
    _ESCALATE_ACTION,
    _REJECT_ACTION,
    ASSOCIATE_REPORT_SORTABLE_COLUMNS,
    INVOICE_REPORT_SORTABLE_COLUMNS,
)
from src.core.workflow.invoice_workflow_buckets import (
    DashboardBucket,
    dashboard_bucket_filter,
)
from src.data.models.postgres.audit_log import AuditLog
from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
    POResolutionCandidateType,
    UserRole,
    VendorStatus,
)
from src.data.models.postgres.invoice_extracted_vendor import (
    InvoiceExtractedVendor,
)
from src.data.models.postgres.invoice_po_mapping import InvoicePOMapping
from src.data.models.postgres.invoice_po_resolution_groups import (
    InvoicePOResolutionGroup,
    InvoicePOResolutionGroupItem,
)
from src.data.models.postgres.invoice_validation_issues import (
    InvoiceValidationIssue,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.purchase_orders import PurchaseOrder
from src.data.models.postgres.users import User
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.base_repo import BaseRepository
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)
from src.schemas.report_schema import (
    FinanceAssociateReportQueryParams,
    InvoiceReportQueryParams,
)
from src.utils.report_issue_severity import (
    issue_severity_expression,
    severity_rank_expression,
)

_RESOLVED_CANDIDATE_TYPES = (
    POResolutionCandidateType.RESOLVED,
    POResolutionCandidateType.RECOVERED,
)

_NEEDS_REVIEW_OUTCOMES = (
    InvoiceValidationOutcome.RECOVERED,
    InvoiceValidationOutcome.AMBIGUOUS,
    InvoiceValidationOutcome.UNRESOLVED,
    InvoiceValidationOutcome.DUPLICATE,
)

_SEVERITY_RANK_TO_LABEL = {
    4: ReportIssueSeverity.CRITICAL.value,
    3: ReportIssueSeverity.HIGH.value,
    2: ReportIssueSeverity.MEDIUM.value,
    1: ReportIssueSeverity.LOW.value,
}


@dataclass(frozen=True, slots=True)
class InvoiceReportRow:
    invoice_id: UUID
    invoice_number: str | None
    invoice_date: date | None
    due_date: date | None
    invoice_status: str | None
    validation_outcome: str | None
    total_amount: Decimal | None
    tax_amount: Decimal | None
    currency: str | None
    vendor_name: str | None
    vendor_gstin: str | None
    vendor_email: str | None
    company_name: str | None
    po_number: str | None
    po_date: date | None
    po_status: str | None
    assigned_finance_associate: str | None
    assigned_finance_manager: str | None
    resolution_type: str | None
    validation_issue_count: int
    highest_issue_severity: str | None
    workflow_status: str | None
    approved_by: str | None
    rejected_by: str | None
    escalated_by: str | None


@dataclass(frozen=True, slots=True)
class FinanceAssociatePerformanceRow:
    associate_id: UUID
    associate_name: str
    report_date: date | None
    total_assigned: int
    approved: int
    rejected: int
    needs_review: int
    ready_for_approval: int
    ready_to_pay: int
    overdue: int
    escalated: int
    resolved_count: int
    recovered_count: int


@dataclass(frozen=True, slots=True)
class VendorOptionRow:
    id: UUID
    vendor_name: str


@dataclass(frozen=True, slots=True)
class FinanceAssociateOptionRow:
    id: UUID
    name: str


class ReportRepository(BaseRepository):
    async def list_vendor_options(self) -> list[VendorOptionRow]:
        result = await self.execute(
            select(
                VendorMaster.id,
                VendorMaster.vendor_name,
            )
            .where(
                VendorMaster.status == VendorStatus.ACTIVE,
            )
            .order_by(
                VendorMaster.vendor_name,
            ),
        )

        return [
            VendorOptionRow(
                id=row.id,
                vendor_name=row.vendor_name,
            )
            for row in result.all()
        ]

    async def list_finance_associate_options(self) -> list[FinanceAssociateOptionRow]:
        result = await self.execute(
            select(
                User.id,
                User.name,
            )
            .where(
                User.role == UserRole.FINANCE_ASSOCIATE,
                User.is_active.is_(
                    True,
                ),
            )
            .order_by(
                User.name,
            ),
        )

        return [
            FinanceAssociateOptionRow(
                id=row.id,
                name=row.name,
            )
            for row in result.all()
        ]

    async def list_invoice_report(
        self,
        *,
        params: InvoiceReportQueryParams,
        scope_associate_id: UUID | None,
    ) -> tuple[list[InvoiceReportRow], int]:
        primary_po = self._primary_po_subquery()
        filters = self._build_invoice_report_filters(
            params=params,
            scope_associate_id=scope_associate_id,
            primary_po=primary_po,
        )

        count_result = await self.execute(
            select(
                func.count(
                    func.distinct(
                        Invoice.id,
                    ),
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
            .outerjoin(
                primary_po,
                primary_po.c.invoice_id == Invoice.id,
            )
            .where(
                filters,
            ),
        )
        total_records = int(
            count_result.scalar_one(),
        )

        query = self._invoice_report_query(
            params=params,
            scope_associate_id=scope_associate_id,
            primary_po=primary_po,
        )

        result = await self.execute(
            query.offset(
                params.offset,
            ).limit(
                params.page_size,
            ),
        )

        return [
            self._map_invoice_report_row(
                row,
            )
            for row in result.all()
        ], total_records

    async def list_invoice_report_for_export(
        self,
        *,
        params: InvoiceReportQueryParams,
        scope_associate_id: UUID | None,
    ) -> list[InvoiceReportRow]:
        primary_po = self._primary_po_subquery()
        result = await self.execute(
            self._invoice_report_query(
                params=params,
                scope_associate_id=scope_associate_id,
                primary_po=primary_po,
            ),
        )

        return [
            self._map_invoice_report_row(
                row,
            )
            for row in result.all()
        ]

    async def list_associate_performance(
        self,
        *,
        params: FinanceAssociateReportQueryParams,
        scope_associate_id: UUID | None,
    ) -> tuple[list[FinanceAssociatePerformanceRow], int]:
        base = self._associate_performance_subquery(
            params=params,
            scope_associate_id=scope_associate_id,
        )

        count_result = await self.execute(
            select(
                func.count(),
            ).select_from(
                base,
            ),
        )
        total_records = int(
            count_result.scalar_one(),
        )

        sort_by = (
            params.sort_by
            if params.sort_by in ASSOCIATE_REPORT_SORTABLE_COLUMNS
            else (
                "report_date"
                if params.view_mode == ReportAssociateViewMode.DAYWISE
                else "associate_name"
            )
        )
        sort_column = column(
            sort_by,
        )
        order_expr = (
            sort_column.desc()
            if params.sort_dir.lower() == "desc"
            else sort_column.asc()
        )

        result = await self.execute(
            select(
                base,
            )
            .order_by(
                order_expr,
            )
            .offset(
                params.offset,
            )
            .limit(
                params.page_size,
            ),
        )

        rows = [
            FinanceAssociatePerformanceRow(
                associate_id=row.associate_id,
                associate_name=row.associate_name,
                report_date=row.report_date,
                total_assigned=int(
                    row.total_assigned or 0,
                ),
                approved=int(
                    row.approved or 0,
                ),
                rejected=int(
                    row.rejected or 0,
                ),
                needs_review=int(
                    row.needs_review or 0,
                ),
                ready_for_approval=int(
                    row.ready_for_approval or 0,
                ),
                ready_to_pay=int(
                    row.ready_to_pay or 0,
                ),
                overdue=int(
                    row.overdue or 0,
                ),
                escalated=int(
                    row.escalated or 0,
                ),
                resolved_count=int(
                    row.resolved_count or 0,
                ),
                recovered_count=int(
                    row.recovered_count or 0,
                ),
            )
            for row in result.all()
        ]

        return rows, total_records

    async def list_associate_performance_for_export(
        self,
        *,
        params: FinanceAssociateReportQueryParams,
        scope_associate_id: UUID | None,
    ) -> list[FinanceAssociatePerformanceRow]:
        rows, _ = await self.list_associate_performance(
            params=params.model_copy(
                update={
                    "page": 1,
                    "page_size": 100_000,
                },
            ),
            scope_associate_id=scope_associate_id,
        )

        return rows

    def _invoice_report_query(
        self,
        *,
        params: InvoiceReportQueryParams,
        scope_associate_id: UUID | None,
        primary_po,
    ):
        associate_user = aliased(
            User,
        )
        manager_user = aliased(
            User,
        )
        approved_user = aliased(
            User,
        )
        rejected_user = aliased(
            User,
        )
        escalated_user = aliased(
            User,
        )

        issue_stats = self._issue_stats_subquery()
        approved_by_subq = self._latest_audit_actor_subquery(
            _APPLY_ACTION,
        )
        rejected_by_subq = self._latest_audit_actor_subquery(
            _REJECT_ACTION,
        )
        escalated_by_subq = self._latest_audit_actor_subquery(
            _ESCALATE_ACTION,
        )
        associate_owner = self._primary_associate_owner_subquery()
        workflow_status = self._workflow_status_expression()

        filters = self._build_invoice_report_filters(
            params=params,
            scope_associate_id=scope_associate_id,
            primary_po=primary_po,
        )

        return (
            select(
                Invoice.id.label(
                    "invoice_id",
                ),
                Invoice.invoice_number,
                Invoice.invoice_date,
                Invoice.due_date,
                workflow_status.label(
                    "invoice_status",
                ),
                Invoice.validation_outcome,
                Invoice.total_amount,
                Invoice.tax_amount,
                Invoice.currency,
                func.coalesce(
                    VendorMaster.vendor_name,
                    InvoiceExtractedVendor.vendor_name,
                ).label(
                    "vendor_name",
                ),
                func.coalesce(
                    VendorMaster.gstin,
                    InvoiceExtractedVendor.vendor_gstin,
                ).label(
                    "vendor_gstin",
                ),
                func.coalesce(
                    VendorMaster.email,
                    InvoiceExtractedVendor.vendor_email,
                ).label(
                    "vendor_email",
                ),
                Invoice.company_name,
                primary_po.c.po_number,
                primary_po.c.po_date,
                primary_po.c.po_status,
                associate_user.name.label(
                    "assigned_finance_associate",
                ),
                manager_user.name.label(
                    "assigned_finance_manager",
                ),
                case(
                    (
                        Invoice.validation_outcome
                        == InvoiceValidationOutcome.RESOLVED,
                        literal(
                            "Resolved",
                        ),
                    ),
                    (
                        Invoice.validation_outcome
                        == InvoiceValidationOutcome.RECOVERED,
                        literal(
                            "Recovered",
                        ),
                    ),
                    else_=None,
                ).label(
                    "resolution_type",
                ),
                func.coalesce(
                    issue_stats.c.issue_count,
                    0,
                ).label(
                    "validation_issue_count",
                ),
                issue_stats.c.max_severity_rank,
                workflow_status.label(
                    "workflow_status",
                ),
                approved_user.name.label(
                    "approved_by",
                ),
                rejected_user.name.label(
                    "rejected_by",
                ),
                escalated_user.name.label(
                    "escalated_by",
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
            .outerjoin(
                primary_po,
                primary_po.c.invoice_id == Invoice.id,
            )
            .outerjoin(
                associate_owner,
                associate_owner.c.invoice_id == Invoice.id,
            )
            .outerjoin(
                associate_user,
                associate_user.id == associate_owner.c.associate_id,
            )
            .outerjoin(
                manager_user,
                manager_user.id == Invoice.assigned_manager_id,
            )
            .outerjoin(
                approved_by_subq,
                approved_by_subq.c.invoice_id == Invoice.id,
            )
            .outerjoin(
                approved_user,
                approved_user.id == approved_by_subq.c.performed_by,
            )
            .outerjoin(
                rejected_by_subq,
                rejected_by_subq.c.invoice_id == Invoice.id,
            )
            .outerjoin(
                rejected_user,
                rejected_user.id == rejected_by_subq.c.performed_by,
            )
            .outerjoin(
                escalated_by_subq,
                escalated_by_subq.c.invoice_id == Invoice.id,
            )
            .outerjoin(
                escalated_user,
                escalated_user.id == escalated_by_subq.c.performed_by,
            )
            .outerjoin(
                issue_stats,
                issue_stats.c.invoice_id == Invoice.id,
            )
            .where(
                filters,
            )
            .order_by(
                *self._invoice_report_order_by(
                    params.sort_by,
                    params.sort_dir,
                    primary_po=primary_po,
                ),
            )
        )

    def _associate_performance_subquery(
        self,
        *,
        params: FinanceAssociateReportQueryParams,
        scope_associate_id: UUID | None,
    ):
        associate_filter = self._resolve_associate_scope_filter(
            params=params,
            scope_associate_id=scope_associate_id,
        )
        date_filter = self._invoice_date_filter(
            params.from_date,
            params.to_date,
        )
        pairs = self._invoice_associate_pairs_subquery()
        search_filter = self._associate_search_filter(
            params.search,
        )
        invoice_date_value = func.coalesce(
            Invoice.invoice_date,
            cast(
                Invoice.created_at,
                Date,
            ),
        )
        daywise = params.view_mode == ReportAssociateViewMode.DAYWISE

        select_columns = [
            User.id.label(
                "associate_id",
            ),
            User.name.label(
                "associate_name",
            ),
        ]

        if daywise:
            select_columns.append(
                invoice_date_value.label(
                    "report_date",
                ),
            )
        else:
            select_columns.append(
                literal(
                    None,
                ).label(
                    "report_date",
                ),
            )

        select_columns.extend(
            [
                func.count(
                    func.distinct(
                        pairs.c.invoice_id,
                    ),
                ).label(
                    "total_assigned",
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
                            Invoice.invoice_status == InvoiceStatus.REJECTED,
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
                            and_(
                                Invoice.invoice_status
                                == InvoiceStatus.UNDER_REVIEW,
                                Invoice.validation_outcome.in_(
                                    _NEEDS_REVIEW_OUTCOMES,
                                ),
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "needs_review",
                ),
                func.sum(
                    case(
                        (
                            and_(
                                Invoice.invoice_status
                                == InvoiceStatus.UNDER_REVIEW,
                                Invoice.validation_outcome
                                == InvoiceValidationOutcome.RESOLVED,
                            ),
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "ready_for_approval",
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
                    "ready_to_pay",
                ),
                func.sum(
                    case(
                        (
                            Invoice.invoice_status == InvoiceStatus.OVERDUE,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "overdue",
                ),
                func.sum(
                    case(
                        (
                            Invoice.invoice_status == InvoiceStatus.ESCALATED,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "escalated",
                ),
                func.sum(
                    case(
                        (
                            Invoice.validation_outcome
                            == InvoiceValidationOutcome.RESOLVED,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "resolved_count",
                ),
                func.sum(
                    case(
                        (
                            Invoice.validation_outcome
                            == InvoiceValidationOutcome.RECOVERED,
                            1,
                        ),
                        else_=0,
                    ),
                ).label(
                    "recovered_count",
                ),
                case(
                    (
                        func.count(
                            func.distinct(
                                pairs.c.invoice_id,
                            ),
                        )
                        > 0,
                        (
                            func.sum(
                                case(
                                    (
                                        Invoice.invoice_status
                                        == InvoiceStatus.READY_TO_PAY,
                                        1,
                                    ),
                                    else_=0,
                                ),
                            )
                            * 100.0
                            / func.count(
                                func.distinct(
                                    pairs.c.invoice_id,
                                ),
                            )
                        ),
                    ),
                    else_=0,
                ).label(
                    "approval_rate",
                ),
                case(
                    (
                        func.count(
                            func.distinct(
                                pairs.c.invoice_id,
                            ),
                        )
                        > 0,
                        (
                            func.sum(
                                case(
                                    (
                                        Invoice.invoice_status
                                        == InvoiceStatus.REJECTED,
                                        1,
                                    ),
                                    else_=0,
                                ),
                            )
                            * 100.0
                            / func.count(
                                func.distinct(
                                    pairs.c.invoice_id,
                                ),
                            )
                        ),
                    ),
                    else_=0,
                ).label(
                    "rejection_rate",
                ),
            ],
        )

        group_by_columns = [
            User.id,
            User.name,
        ]

        if daywise:
            group_by_columns.append(
                invoice_date_value,
            )

        return (
            select(
                *select_columns,
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
                User.role == UserRole.FINANCE_ASSOCIATE,
                date_filter,
                associate_filter,
                search_filter,
            )
            .group_by(
                *group_by_columns,
            )
        ).subquery()

    def _build_invoice_report_filters(
        self,
        *,
        params: InvoiceReportQueryParams,
        scope_associate_id: UUID | None,
        primary_po,
    ) -> ColumnElement[bool]:
        conditions: list[ColumnElement[bool]] = [
            self._invoice_date_filter(
                params.from_date,
                params.to_date,
            ),
        ]

        if scope_associate_id is not None:
            conditions.append(
                InvoiceOwnershipRepository.associate_ownership_filter(
                    scope_associate_id,
                ),
            )

        if params.finance_associate_id is not None:
            conditions.append(
                InvoiceOwnershipRepository.associate_ownership_filter(
                    params.finance_associate_id,
                ),
            )

        if params.vendor_id is not None:
            conditions.append(
                self._vendor_filter(
                    params.vendor_id,
                ),
            )

        if params.invoice_status is not None:
            conditions.append(
                self._invoice_status_filter(
                    params.invoice_status,
                ),
            )

        if params.validation_outcome is not None:
            conditions.append(
                Invoice.validation_outcome
                == InvoiceValidationOutcome(
                    params.validation_outcome.value,
                ),
            )

        if params.overdue == ReportOverdueFilter.YES:
            conditions.append(
                Invoice.invoice_status == InvoiceStatus.OVERDUE,
            )
        elif params.overdue == ReportOverdueFilter.NO:
            conditions.append(
                or_(
                    Invoice.invoice_status.is_(
                        None,
                    ),
                    Invoice.invoice_status != InvoiceStatus.OVERDUE,
                ),
            )

        if params.po_number:
            conditions.append(
                primary_po.c.po_number.ilike(
                    f"%{params.po_number.strip()}%",
                ),
            )

        if params.invoice_number:
            conditions.append(
                Invoice.invoice_number.ilike(
                    f"%{params.invoice_number.strip()}%",
                ),
            )

        if params.validation_node or params.issue_severity:
            conditions.append(
                self._validation_issue_filter(
                    validation_node=params.validation_node.value
                    if params.validation_node
                    else None,
                    issue_severity=params.issue_severity.value
                    if params.issue_severity
                    else None,
                ),
            )

        if params.search:
            search_term = f"%{params.search.strip()}%"
            conditions.append(
                or_(
                    Invoice.invoice_number.ilike(
                        search_term,
                    ),
                    Invoice.company_name.ilike(
                        search_term,
                    ),
                    func.coalesce(
                        VendorMaster.vendor_name,
                        InvoiceExtractedVendor.vendor_name,
                    ).ilike(
                        search_term,
                    ),
                    primary_po.c.po_number.ilike(
                        search_term,
                    ),
                ),
            )

        return and_(
            *conditions,
        )

    @staticmethod
    def _vendor_filter(
        vendor_id: UUID,
    ) -> ColumnElement[bool]:
        return or_(
            Invoice.vendor_id == vendor_id,
            exists(
                select(
                    1,
                )
                .select_from(
                    InvoiceExtractedVendor,
                )
                .join(
                    VendorMaster,
                    VendorMaster.id == vendor_id,
                )
                .where(
                    InvoiceExtractedVendor.invoice_id == Invoice.id,
                    or_(
                        InvoiceExtractedVendor.vendor_master_id == vendor_id,
                        and_(
                            VendorMaster.gstin.isnot(
                                None,
                            ),
                            InvoiceExtractedVendor.vendor_gstin
                            == VendorMaster.gstin,
                        ),
                        func.lower(
                            InvoiceExtractedVendor.vendor_name,
                        )
                        == func.lower(
                            VendorMaster.vendor_name,
                        ),
                    ),
                ),
            ),
        )

    @staticmethod
    def _invoice_status_filter(
        status: ReportInvoiceStatus,
    ) -> ColumnElement[bool]:
        if status == ReportInvoiceStatus.READY_FOR_APPROVAL:
            return dashboard_bucket_filter(
                DashboardBucket.READY_FOR_APPROVAL,
            )

        if status == ReportInvoiceStatus.NEEDS_REVIEW:
            return dashboard_bucket_filter(
                DashboardBucket.NEEDS_REVIEW,
            )

        if status == ReportInvoiceStatus.READY_TO_PAY:
            return Invoice.invoice_status == InvoiceStatus.READY_TO_PAY

        if status == ReportInvoiceStatus.OVERDUE:
            return Invoice.invoice_status == InvoiceStatus.OVERDUE

        if status == ReportInvoiceStatus.REJECTED:
            return Invoice.invoice_status == InvoiceStatus.REJECTED

        if status == ReportInvoiceStatus.ESCALATED:
            return Invoice.invoice_status == InvoiceStatus.ESCALATED

        raise ValueError(
            f"Unsupported invoice status filter: {status}",
        )

    @staticmethod
    def _validation_issue_filter(
        *,
        validation_node: str | None,
        issue_severity: str | None,
    ) -> ColumnElement[bool]:
        severity_expr = issue_severity_expression()

        issue_conditions: list[ColumnElement[bool]] = []

        if validation_node is not None:
            issue_conditions.append(
                InvoiceValidationIssue.check_stage == validation_node,
            )

        if issue_severity is not None:
            issue_conditions.append(
                severity_expr == issue_severity,
            )

        return exists(
            select(
                1,
            )
            .select_from(
                InvoiceValidationIssue,
            )
            .where(
                InvoiceValidationIssue.invoice_id == Invoice.id,
                *issue_conditions,
            ),
        )

    @staticmethod
    def _invoice_date_filter(
        from_date: date | None,
        to_date: date | None,
    ) -> ColumnElement[bool]:
        invoice_date_value = func.coalesce(
            Invoice.invoice_date,
            cast(
                Invoice.created_at,
                Date,
            ),
        )

        conditions: list[ColumnElement[bool]] = []

        if from_date is not None:
            conditions.append(
                invoice_date_value >= from_date,
            )

        if to_date is not None:
            conditions.append(
                invoice_date_value <= to_date,
            )

        if not conditions:
            return true()

        return and_(
            *conditions,
        )

    @staticmethod
    def _workflow_status_expression() -> ColumnElement[str]:
        return case(
            (
                Invoice.invoice_status == InvoiceStatus.OVERDUE,
                literal(
                    ReportInvoiceStatus.OVERDUE.value,
                ),
            ),
            (
                Invoice.invoice_status == InvoiceStatus.READY_TO_PAY,
                literal(
                    ReportInvoiceStatus.READY_TO_PAY.value,
                ),
            ),
            (
                Invoice.invoice_status == InvoiceStatus.REJECTED,
                literal(
                    ReportInvoiceStatus.REJECTED.value,
                ),
            ),
            (
                dashboard_bucket_filter(
                    DashboardBucket.READY_FOR_APPROVAL,
                ),
                literal(
                    ReportInvoiceStatus.READY_FOR_APPROVAL.value,
                ),
            ),
            (
                dashboard_bucket_filter(
                    DashboardBucket.NEEDS_REVIEW,
                ),
                literal(
                    ReportInvoiceStatus.NEEDS_REVIEW.value,
                ),
            ),
            else_=func.coalesce(
                cast(
                    Invoice.invoice_status,
                    String,
                ),
                literal(
                    "unknown",
                ),
            ),
        )

    @staticmethod
    def _primary_po_subquery():
        selected_group_po = (
            select(
                InvoicePOResolutionGroup.invoice_id.label(
                    "invoice_id",
                ),
                PurchaseOrder.po_number.label(
                    "po_number",
                ),
                PurchaseOrder.po_date.label(
                    "po_date",
                ),
                cast(
                    PurchaseOrder.status,
                    String,
                ).label(
                    "po_status",
                ),
                func.row_number()
                .over(
                    partition_by=InvoicePOResolutionGroup.invoice_id,
                    order_by=InvoicePOResolutionGroup.created_at.desc(),
                )
                .label(
                    "row_num",
                ),
            )
            .select_from(
                InvoicePOResolutionGroup,
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
                InvoicePOResolutionGroup.is_selected.is_(
                    True,
                ),
            )
        )

        mapping_po = (
            select(
                InvoicePOMapping.invoice_id.label(
                    "invoice_id",
                ),
                PurchaseOrder.po_number.label(
                    "po_number",
                ),
                PurchaseOrder.po_date.label(
                    "po_date",
                ),
                cast(
                    PurchaseOrder.status,
                    String,
                ).label(
                    "po_status",
                ),
                func.row_number()
                .over(
                    partition_by=InvoicePOMapping.invoice_id,
                    order_by=InvoicePOMapping.created_at.asc(),
                )
                .label(
                    "row_num",
                ),
            )
            .select_from(
                InvoicePOMapping,
            )
            .join(
                PurchaseOrder,
                InvoicePOMapping.po_id == PurchaseOrder.id,
            )
        )

        combined = union(
            selected_group_po,
            mapping_po,
        ).subquery()

        return (
            select(
                combined.c.invoice_id,
                combined.c.po_number,
                combined.c.po_date,
                combined.c.po_status,
            )
            .where(
                combined.c.row_num == 1,
            )
            .subquery(
                "primary_po",
            )
        )

    @staticmethod
    def _primary_associate_owner_subquery():
        pairs = ReportRepository._invoice_associate_pairs_subquery()

        ranked = (
            select(
                pairs.c.invoice_id,
                pairs.c.associate_id,
                func.row_number()
                .over(
                    partition_by=pairs.c.invoice_id,
                    order_by=pairs.c.associate_id,
                )
                .label(
                    "row_num",
                ),
            ).subquery()
        )

        return (
            select(
                ranked.c.invoice_id,
                ranked.c.associate_id,
            )
            .where(
                ranked.c.row_num == 1,
            )
            .subquery(
                "primary_associate_owner",
            )
        )

    @staticmethod
    def _issue_stats_subquery():
        severity_expr = issue_severity_expression()
        severity_rank = severity_rank_expression(
            severity_expr,
        )

        ranked = (
            select(
                InvoiceValidationIssue.invoice_id.label(
                    "invoice_id",
                ),
                severity_rank.label(
                    "severity_rank",
                ),
            ).subquery()
        )

        return (
            select(
                ranked.c.invoice_id,
                func.count().label(
                    "issue_count",
                ),
                func.max(
                    ranked.c.severity_rank,
                ).label(
                    "max_severity_rank",
                ),
            )
            .group_by(
                ranked.c.invoice_id,
            )
            .subquery(
                "issue_stats",
            )
        )

    @staticmethod
    def _latest_audit_actor_subquery(
        action: str,
    ):
        ranked = (
            select(
                AuditLog.invoice_id.label(
                    "invoice_id",
                ),
                AuditLog.performed_by.label(
                    "performed_by",
                ),
                func.row_number()
                .over(
                    partition_by=AuditLog.invoice_id,
                    order_by=AuditLog.created_at.desc(),
                )
                .label(
                    "row_num",
                ),
            )
            .where(
                AuditLog.action == action,
                AuditLog.performed_by.is_not(
                    None,
                ),
            )
            .subquery()
        )

        return (
            select(
                ranked.c.invoice_id,
                ranked.c.performed_by,
            )
            .where(
                ranked.c.row_num == 1,
            )
            .subquery(
                f"audit_{action.lower()}",
            )
        )

    def _invoice_report_order_by(
        self,
        sort_by: str,
        sort_dir: str,
        *,
        primary_po,
    ):
        if sort_by not in INVOICE_REPORT_SORTABLE_COLUMNS:
            sort_by = "invoice_date"

        column_map = {
            "invoice_number": Invoice.invoice_number,
            "invoice_date": Invoice.invoice_date,
            "due_date": Invoice.due_date,
            "invoice_status": self._workflow_status_expression(),
            "validation_outcome": Invoice.validation_outcome,
            "total_amount": Invoice.total_amount,
            "vendor_name": func.coalesce(
                VendorMaster.vendor_name,
                InvoiceExtractedVendor.vendor_name,
            ),
            "company_name": Invoice.company_name,
            "po_number": primary_po.c.po_number,
            "created_at": Invoice.created_at,
        }

        sort_column = column_map.get(
            sort_by,
            Invoice.invoice_date,
        )
        direction = (
            sort_column.desc()
            if sort_dir.lower() == "desc"
            else sort_column.asc()
        )

        return (
            direction,
            Invoice.created_at.desc(),
        )

    @staticmethod
    def _associate_search_filter(
        search: str | None,
    ) -> ColumnElement[bool]:
        if not search:
            return true()

        return User.name.ilike(
            f"%{search.strip()}%",
        )

    @staticmethod
    def _resolve_associate_scope_filter(
        *,
        params: FinanceAssociateReportQueryParams,
        scope_associate_id: UUID | None,
    ) -> ColumnElement[bool]:
        if scope_associate_id is not None:
            return User.id == scope_associate_id

        if params.finance_associate_id is not None:
            return User.id == params.finance_associate_id

        return true()

    @staticmethod
    def _map_invoice_report_row(
        row,
    ) -> InvoiceReportRow:
        validation_outcome = (
            row.validation_outcome.value
            if row.validation_outcome is not None
            else None
        )
        max_rank = row.max_severity_rank
        highest_severity = (
            _SEVERITY_RANK_TO_LABEL.get(
                int(
                    max_rank,
                ),
            )
            if max_rank is not None
            else None
        )

        workflow_status = row.workflow_status

        return InvoiceReportRow(
            invoice_id=row.invoice_id,
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
            due_date=row.due_date,
            invoice_status=workflow_status,
            validation_outcome=validation_outcome,
            total_amount=row.total_amount,
            tax_amount=row.tax_amount,
            currency=row.currency,
            vendor_name=row.vendor_name,
            vendor_gstin=row.vendor_gstin,
            vendor_email=row.vendor_email,
            company_name=row.company_name,
            po_number=row.po_number,
            po_date=row.po_date,
            po_status=row.po_status,
            assigned_finance_associate=row.assigned_finance_associate,
            assigned_finance_manager=row.assigned_finance_manager,
            resolution_type=row.resolution_type,
            validation_issue_count=int(
                row.validation_issue_count or 0,
            ),
            highest_issue_severity=highest_severity,
            workflow_status=workflow_status,
            approved_by=row.approved_by,
            rejected_by=row.rejected_by,
            escalated_by=row.escalated_by,
        )

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
