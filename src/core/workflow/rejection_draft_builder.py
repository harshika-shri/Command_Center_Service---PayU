from __future__ import annotations


class RejectionDraftBuilder:
    @staticmethod
    def build_subject(
        invoice_number: str | None,
        invoice_id: str,
    ) -> str:
        display_number = invoice_number or invoice_id

        return f"Invoice Rejection - {display_number}"

    @staticmethod
    def build_body(
        invoice_number: str | None,
        invoice_id: str,
        issues: list[str],
        rejection_reason: str | None,
    ) -> str:
        display_number = invoice_number or invoice_id
        bullet_points = "\n".join(
            f"• {issue}"
            for issue in issues
        )
        reason_block = ""

        if rejection_reason:
            reason_block = (
                f"\nReview note: {rejection_reason}\n"
            )

        return (
            "Dear Vendor,\n\n"
            f"We have completed our review of Invoice {display_number}.\n\n"
            "At this time, we are unable to process the invoice due to "
            "the following issues:\n\n"
            f"{bullet_points}\n"
            f"{reason_block}\n"
            "Please review the above items and provide corrected "
            "documentation for further review.\n\n"
            "Regards,\n"
            "Finance Team"
        )
