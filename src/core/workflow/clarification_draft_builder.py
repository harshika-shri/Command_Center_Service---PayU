from __future__ import annotations


class ClarificationDraftBuilder:
    @staticmethod
    def build_subject(
        invoice_number: str | None,
        invoice_id: str,
    ) -> str:
        display_number = invoice_number or invoice_id

        return f"Clarification Required - Invoice {display_number}"

    @staticmethod
    def build_body(
        invoice_number: str | None,
        invoice_id: str,
        clarification_points: list[str],
    ) -> str:
        display_number = invoice_number or invoice_id
        numbered_points = "\n".join(
            f"{index}. {point}"
            for index, point in enumerate(
                clarification_points,
                start=1,
            )
        )

        return (
            "Dear Vendor,\n\n"
            f"During our review of invoice {display_number}, "
            "we identified a few items requiring clarification.\n\n"
            f"{numbered_points}\n\n"
            "Please provide clarification and supporting information.\n\n"
            "Regards,\n"
            "Finance Team"
        )

    @staticmethod
    def plain_text_to_html(
        body: str,
    ) -> str:
        escaped = (
            body.replace(
                "&",
                "&amp;",
            )
            .replace(
                "<",
                "&lt;",
            )
            .replace(
                ">",
                "&gt;",
            )
            .replace(
                "\n",
                "<br>",
            )
        )

        return (
            "<html><body style='font-family: sans-serif;'>"
            f"{escaped}"
            "</body></html>"
        )
