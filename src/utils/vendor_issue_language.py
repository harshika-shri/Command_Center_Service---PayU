from __future__ import annotations

import re

OPEN_ISSUE_MESSAGES: dict[str, str] = {
    "MISSING_INVOICE_NUMBER": (
        "Invoice number is missing on the submitted invoice."
    ),
    "VENDOR_NOT_FOUND": (
        "The vendor information on the invoice could not be validated "
        "against our records."
    ),
    "VENDOR_DETAILS_MISSING": (
        "Vendor name, GSTIN, and address could not be extracted from "
        "the invoice."
    ),
    "MISSING_VENDOR_NAME": (
        "Vendor name could not be extracted from the invoice."
    ),
    "MISSING_VENDOR_GSTIN": (
        "Vendor GSTIN could not be extracted from the invoice."
    ),
    "MISSING_VENDOR_ADDRESS": (
        "Vendor address could not be extracted from the invoice."
    ),
    "VENDOR_NAME_MISMATCH": (
        "The vendor name on the invoice does not match our vendor records."
    ),
    "PO_NOT_FOUND": (
        "The referenced purchase order number was not found."
    ),
    "PO_MISSING": (
        "No purchase order reference could be identified on the invoice."
    ),
    "INVALID_PO_REFERENCE": (
        "The purchase order reference on the invoice could not be validated."
    ),
    "PO_UNRESOLVED": (
        "A suitable purchase order could not be identified for this invoice."
    ),
    "PO_AMBIGUOUS": (
        "Multiple purchase orders may apply to this invoice and could not "
        "be confirmed automatically."
    ),
    "MISSING_PO_COVERAGE": (
        "One or more invoice lines lack purchase order coverage."
    ),
    "UNMATCHED_LINE_ITEM": (
        "One or more invoice lines could not be matched to purchase orders."
    ),
    "AMBIGUOUS_LINE_MATCH": (
        "Multiple valid line allocations were identified for this invoice."
    ),
    "QUANTITY_EXCEEDS_ORDERED": (
        "Billed quantity exceeds the approved purchase order quantity."
    ),
    "QUANTITY_EXCEEDS_REMAINING": (
        "Billed quantity exceeds the remaining purchase order quantity."
    ),
    "UNIT_PRICE_MISMATCH": (
        "The unit price differs from the approved purchase order."
    ),
    "LINE_TOTAL_MISMATCH": (
        "A line total does not match the billed quantity and unit price."
    ),
    "TOTAL_AMOUNT_MISMATCH": (
        "The invoice amount does not match the approved purchase order amount."
    ),
    "INVOICE_TAX_MISMATCH": (
        "The tax amount on the invoice differs from the expected value."
    ),
    "SUBTOTAL_MISMATCH": (
        "The invoice subtotal differs from the sum of line totals."
    ),
    "DUPLICATE_INVOICE_NUMBER": (
        "This invoice number has already been used for this vendor."
    ),
    "POTENTIAL_DUPLICATE_INVOICE": (
        "This invoice closely resembles another invoice already received."
    ),
}

_INTERNAL_CODE_PATTERN = re.compile(
    r"^[A-Z0-9_]+$",
)


def vendor_friendly_issue_message(
    *,
    issue_code: str,
    description: str,
) -> str:
    normalized_code = issue_code.strip().upper()

    mapped = OPEN_ISSUE_MESSAGES.get(
        normalized_code,
    )

    if mapped:
        return mapped

    cleaned_description = description.strip()

    if cleaned_description and not _INTERNAL_CODE_PATTERN.match(
        cleaned_description,
    ):
        return cleaned_description

    return (
        "A discrepancy was identified during invoice review that requires "
        "corrective action."
    )


def deduplicate_issue_messages(
    messages: list[str],
) -> list[str]:
    seen: set[str] = set()
    unique_messages: list[str] = []

    for message in messages:
        normalized = re.sub(
            r"\s+",
            " ",
            message.strip(),
        )

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        unique_messages.append(normalized)

    return unique_messages
