from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import ColumnElement, and_, exists, or_, select, true

from src.data.models.postgres.enums import (
    InvoiceStatus,
    InvoiceValidationOutcome,
)
from src.data.models.postgres.invoice_po_mapping import InvoicePOMapping
from src.data.models.postgres.invoice_po_resolution_groups import (
    InvoicePOResolutionGroup,
    InvoicePOResolutionGroupItem,
)
from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.purchase_orders import PurchaseOrder
from src.data.models.postgres.vendor_master import VendorMaster
from src.data.repositories.invoice_ownership_repo import (
    InvoiceOwnershipRepository,
)
from src.schemas.report_schema import (
    to_utc_end_exclusive,
    to_utc_start,
)


@dataclass(frozen=True, slots=True)
class InvoiceListFilters:
    search: str | None = None
    invoice_status: str | None = None
    validation_outcome: str | None = None
    vendor_id: UUID | None = None
    associate_id: UUID | None = None
    manager_id: UUID | None = None
    from_date: date | None = None
    to_date: date | None = None


@dataclass(frozen=True, slots=True)
class ReportFilters:
    start_date: date | None = None
    end_date: date | None = None
    invoice_status: str | None = None
    validation_outcome: str | None = None
    vendor_id: UUID | None = None
    associate_id: UUID | None = None
    manager_id: UUID | None = None


class SearchFilterBuilder:
    @staticmethod
    def build_invoice_filters(
        filters: InvoiceListFilters,
    ) -> ColumnElement[bool]:
        conditions: list[ColumnElement[bool]] = []

        search_filter = SearchFilterBuilder._build_search_filter(
            filters.search,
        )

        if search_filter is not None:
            conditions.append(
                search_filter,
            )

        status_filter = SearchFilterBuilder._build_enum_filter(
            value=filters.invoice_status,
            enum_type=InvoiceStatus,
            column=Invoice.invoice_status,
        )

        if status_filter is not None:
            conditions.append(
                status_filter,
            )

        outcome_filter = SearchFilterBuilder._build_enum_filter(
            value=filters.validation_outcome,
            enum_type=InvoiceValidationOutcome,
            column=Invoice.validation_outcome,
        )

        if outcome_filter is not None:
            conditions.append(
                outcome_filter,
            )

        if filters.vendor_id is not None:
            conditions.append(
                Invoice.vendor_id == filters.vendor_id,
            )

        if filters.associate_id is not None:
            conditions.append(
                InvoiceOwnershipRepository.associate_ownership_filter(
                    filters.associate_id,
                ),
            )

        if filters.manager_id is not None:
            conditions.append(
                Invoice.assigned_manager_id == filters.manager_id,
            )

        date_filter = SearchFilterBuilder._build_date_filter(
            from_date=filters.from_date,
            to_date=filters.to_date,
        )

        if date_filter is not None:
            conditions.append(
                date_filter,
            )

        if not conditions:
            return true()

        return and_(
            *conditions,
        )

    @staticmethod
    def build_report_filters(
        filters: ReportFilters,
    ) -> ColumnElement[bool]:
        conditions: list[ColumnElement[bool]] = []

        date_filter = SearchFilterBuilder._build_date_filter(
            from_date=filters.start_date,
            to_date=filters.end_date,
        )

        if date_filter is not None:
            conditions.append(
                date_filter,
            )

        status_filter = SearchFilterBuilder._build_enum_filter(
            value=filters.invoice_status,
            enum_type=InvoiceStatus,
            column=Invoice.invoice_status,
        )

        if status_filter is not None:
            conditions.append(
                status_filter,
            )

        outcome_filter = SearchFilterBuilder._build_enum_filter(
            value=filters.validation_outcome,
            enum_type=InvoiceValidationOutcome,
            column=Invoice.validation_outcome,
        )

        if outcome_filter is not None:
            conditions.append(
                outcome_filter,
            )

        if filters.vendor_id is not None:
            conditions.append(
                Invoice.vendor_id == filters.vendor_id,
            )

        if filters.associate_id is not None:
            conditions.append(
                InvoiceOwnershipRepository.associate_ownership_filter(
                    filters.associate_id,
                ),
            )

        if filters.manager_id is not None:
            conditions.append(
                Invoice.assigned_manager_id == filters.manager_id,
            )

        if not conditions:
            return true()

        return and_(
            *conditions,
        )

    @staticmethod
    def requires_vendor_join(
        filters: InvoiceListFilters,
        *,
        sort_by: str | None = None,
    ) -> bool:
        if filters.search:
            return True

        if sort_by == "vendor_name":
            return True

        return False

    @staticmethod
    def _build_search_filter(
        search: str | None,
    ) -> ColumnElement[bool] | None:
        if search is None:
            return None

        term = search.strip()

        if not term:
            return None

        pattern = f"%{term}%"
        po_filter = SearchFilterBuilder._po_number_search_filter(
            pattern,
        )

        return or_(
            Invoice.invoice_number.ilike(
                pattern,
            ),
            VendorMaster.vendor_name.ilike(
                pattern,
            ),
            po_filter,
        )

    @staticmethod
    def _po_number_search_filter(
        pattern: str,
    ) -> ColumnElement[bool]:
        mapping_match = exists(
            select(
                1,
            )
            .select_from(
                InvoicePOMapping,
            )
            .join(
                PurchaseOrder,
                InvoicePOMapping.po_id == PurchaseOrder.id,
            )
            .where(
                InvoicePOMapping.invoice_id == Invoice.id,
                PurchaseOrder.po_number.ilike(
                    pattern,
                ),
            ),
        )
        resolution_match = exists(
            select(
                1,
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
                InvoicePOResolutionGroup.invoice_id == Invoice.id,
                PurchaseOrder.po_number.ilike(
                    pattern,
                ),
            ),
        )

        return or_(
            mapping_match,
            resolution_match,
        )

    @staticmethod
    def _build_date_filter(
        *,
        from_date: date | None,
        to_date: date | None,
    ) -> ColumnElement[bool] | None:
        conditions: list[ColumnElement[bool]] = []

        if from_date is not None:
            conditions.append(
                Invoice.created_at
                >= to_utc_start(
                    from_date,
                ),
            )

        if to_date is not None:
            conditions.append(
                Invoice.created_at
                < to_utc_end_exclusive(
                    to_date,
                ),
            )

        if not conditions:
            return None

        return and_(
            *conditions,
        )

    @staticmethod
    def _build_enum_filter(
        *,
        value: str | None,
        enum_type: type[InvoiceStatus] | type[InvoiceValidationOutcome],
        column: ColumnElement[object],
    ) -> ColumnElement[bool] | None:
        if value is None:
            return None

        normalized = value.strip()

        if not normalized:
            return None

        try:
            enum_value = enum_type(
                normalized,
            )
        except ValueError:
            return None

        return column == enum_value
