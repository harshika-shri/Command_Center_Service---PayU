from __future__ import annotations

from uuid import UUID

from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.report_constants import (
    REPORT_INVOICE_STATUS_LABELS,
    REPORT_ISSUE_SEVERITY_LABELS,
    REPORT_VALIDATION_NODE_LABELS,
    REPORT_VALIDATION_OUTCOME_LABELS,
    ReportAssociateViewMode,
    ReportOverdueFilter,
)
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.data.repositories.report_repository import (
    FinanceAssociatePerformanceRow,
    ReportRepository,
)
from src.schemas.report_schema import (
    FinanceAssociateOption,
    FinanceAssociatePerformanceItem,
    FinanceAssociatePerformanceListResponse,
    FinanceAssociateReportQueryParams,
    InvoiceReportItem,
    InvoiceReportListResponse,
    InvoiceReportQueryParams,
    ReportFilterOptionsResponse,
    VendorOption,
)
from src.utils.report_export import (
    build_associate_performance_workbook,
    build_invoice_report_workbook,
)


class ReportService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.report_repo = ReportRepository(
            session,
        )

    async def get_filter_options(
        self,
        *,
        current_user: User,
    ) -> ReportFilterOptionsResponse:
        vendors = await self.report_repo.list_vendor_options()
        finance_associates: list[FinanceAssociateOption] = []

        if current_user.role == UserRole.FINANCE_MANAGER:
            associates = await self.report_repo.list_finance_associate_options()
            finance_associates = [
                FinanceAssociateOption(
                    id=row.id,
                    name=row.name,
                )
                for row in associates
            ]

        return ReportFilterOptionsResponse(
            vendors=[
                VendorOption(
                    id=row.id,
                    vendor_name=row.vendor_name,
                )
                for row in vendors
            ],
            finance_associates=finance_associates,
            invoice_statuses=[
                {
                    "value": value,
                    "label": label,
                }
                for value, label in REPORT_INVOICE_STATUS_LABELS.items()
            ],
            validation_outcomes=[
                {
                    "value": value,
                    "label": label,
                }
                for value, label in REPORT_VALIDATION_OUTCOME_LABELS.items()
            ],
            validation_nodes=[
                {
                    "value": value,
                    "label": label,
                }
                for value, label in REPORT_VALIDATION_NODE_LABELS.items()
            ],
            issue_severities=[
                {
                    "value": value,
                    "label": label,
                }
                for value, label in REPORT_ISSUE_SEVERITY_LABELS.items()
            ],
            overdue_options=[
                {
                    "value": option.value,
                    "label": option.value.title(),
                }
                for option in ReportOverdueFilter
            ],
        )

    async def list_invoice_report(
        self,
        *,
        params: InvoiceReportQueryParams,
        current_user: User,
    ) -> InvoiceReportListResponse:
        scope_associate_id = self._associate_scope_id(
            current_user,
        )
        rows, total_records = await self.report_repo.list_invoice_report(
            params=params,
            scope_associate_id=scope_associate_id,
        )

        return InvoiceReportListResponse(
            items=[
                self._map_invoice_row(
                    row,
                )
                for row in rows
            ],
            page=params.page,
            page_size=params.page_size,
            total_records=total_records,
        )

    async def export_invoice_report(
        self,
        *,
        params: InvoiceReportQueryParams,
        current_user: User,
    ) -> Response:
        scope_associate_id = self._associate_scope_id(
            current_user,
        )
        rows = await self.report_repo.list_invoice_report_for_export(
            params=params,
            scope_associate_id=scope_associate_id,
        )
        content = build_invoice_report_workbook(
            rows,
        )

        return Response(
            content=content,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    'attachment; filename="invoice-processing-report.xlsx"'
                ),
            },
        )

    async def list_associate_performance(
        self,
        *,
        params: FinanceAssociateReportQueryParams,
        current_user: User,
    ) -> FinanceAssociatePerformanceListResponse:
        scope_associate_id = self._associate_scope_id(
            current_user,
        )
        rows, total_records = await self.report_repo.list_associate_performance(
            params=params,
            scope_associate_id=scope_associate_id,
        )

        return FinanceAssociatePerformanceListResponse(
            items=[
                self._map_associate_row(
                    row,
                )
                for row in rows
            ],
            page=params.page,
            page_size=params.page_size,
            total_records=total_records,
        )

    async def export_associate_performance(
        self,
        *,
        params: FinanceAssociateReportQueryParams,
        current_user: User,
    ) -> Response:
        scope_associate_id = self._associate_scope_id(
            current_user,
        )
        rows = await self.report_repo.list_associate_performance_for_export(
            params=params,
            scope_associate_id=scope_associate_id,
        )
        approval_rates = [
            self._approval_rate(
                row,
            )
            for row in rows
        ]
        rejection_rates = [
            self._rejection_rate(
                row,
            )
            for row in rows
        ]
        content = build_associate_performance_workbook(
            rows,
            approval_rates=approval_rates,
            rejection_rates=rejection_rates,
            daywise=params.view_mode == ReportAssociateViewMode.DAYWISE,
        )

        return Response(
            content=content,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    'attachment; filename="finance-associate-performance.xlsx"'
                ),
            },
        )

    @staticmethod
    def _associate_scope_id(
        current_user: User,
    ) -> UUID | None:
        if current_user.role == UserRole.FINANCE_ASSOCIATE:
            return current_user.id

        return None

    @staticmethod
    def _approval_rate(
        row: FinanceAssociatePerformanceRow,
    ) -> float:
        if row.total_assigned <= 0:
            return 0.0

        return round(
            (row.ready_to_pay / row.total_assigned) * 100,
            1,
        )

    @staticmethod
    def _rejection_rate(
        row: FinanceAssociatePerformanceRow,
    ) -> float:
        if row.total_assigned <= 0:
            return 0.0

        return round(
            (row.rejected / row.total_assigned) * 100,
            1,
        )

    @staticmethod
    def _map_invoice_row(
        row,
    ) -> InvoiceReportItem:
        return InvoiceReportItem(
            invoice_id=row.invoice_id,
            invoice_number=row.invoice_number,
            invoice_date=row.invoice_date,
            due_date=row.due_date,
            invoice_status=row.invoice_status,
            validation_outcome=row.validation_outcome,
            total_amount=(
                float(
                    row.total_amount,
                )
                if row.total_amount is not None
                else None
            ),
            tax_amount=(
                float(
                    row.tax_amount,
                )
                if row.tax_amount is not None
                else None
            ),
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
            validation_issue_count=row.validation_issue_count,
            highest_issue_severity=row.highest_issue_severity,
            workflow_status=row.workflow_status,
            approved_by=row.approved_by,
            rejected_by=row.rejected_by,
            escalated_by=row.escalated_by,
        )

    @staticmethod
    def _map_associate_row(
        row: FinanceAssociatePerformanceRow,
    ) -> FinanceAssociatePerformanceItem:
        return FinanceAssociatePerformanceItem(
            associate_id=row.associate_id,
            associate_name=row.associate_name,
            report_date=row.report_date,
            total_assigned=row.total_assigned,
            approved=row.approved,
            rejected=row.rejected,
            needs_review=row.needs_review,
            ready_for_approval=row.ready_for_approval,
            ready_to_pay=row.ready_to_pay,
            overdue=row.overdue,
            escalated=row.escalated,
            resolved_count=row.resolved_count,
            recovered_count=row.recovered_count,
            approval_rate=ReportService._approval_rate(
                row,
            ),
            rejection_rate=ReportService._rejection_rate(
                row,
            ),
        )
