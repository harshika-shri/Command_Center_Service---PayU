from __future__ import annotations

from enum import Enum

from sqlalchemy import ColumnElement
from sqlalchemy.sql.elements import UnaryExpression

from src.data.models.postgres.invoices import Invoice
from src.data.models.postgres.vendor_master import VendorMaster


class InvoiceSortField(str, Enum):
    CREATED_AT = "created_at"
    INVOICE_NUMBER = "invoice_number"
    VENDOR_NAME = "vendor_name"
    TOTAL_AMOUNT = "total_amount"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortingHelper:
    _SORT_COLUMNS = {
        InvoiceSortField.CREATED_AT: Invoice.created_at,
        InvoiceSortField.INVOICE_NUMBER: Invoice.invoice_number,
        InvoiceSortField.VENDOR_NAME: VendorMaster.vendor_name,
        InvoiceSortField.TOTAL_AMOUNT: Invoice.total_amount,
    }

    @classmethod
    def resolve_invoice_sort(
        cls,
        *,
        sort_by: str | None,
        sort_order: str | None,
    ) -> tuple[ColumnElement[object], bool]:
        field = InvoiceSortField.CREATED_AT

        if sort_by is not None:
            try:
                field = InvoiceSortField(
                    sort_by,
                )
            except ValueError:
                field = InvoiceSortField.CREATED_AT

        order = SortOrder.DESC

        if sort_order is not None:
            try:
                order = SortOrder(
                    sort_order,
                )
            except ValueError:
                order = SortOrder.DESC

        column = cls._SORT_COLUMNS[
            field,
        ]
        requires_vendor_join = field == InvoiceSortField.VENDOR_NAME

        if order == SortOrder.ASC:
            return column.asc(), requires_vendor_join

        return column.desc(), requires_vendor_join

    @classmethod
    def apply_sort(
        cls,
        *,
        sort_by: str | None,
        sort_order: str | None,
    ) -> UnaryExpression[object]:
        expression, _ = cls.resolve_invoice_sort(
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return expression
