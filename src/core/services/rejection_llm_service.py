from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from src.config.settings import settings
from src.core.exceptions.rejection_exc import (
    RejectionDraftGenerationError,
)

_THINKING_BLOCK_PATTERN = re.compile(
    "<"
    "think"
    r">[\s\S]*?</"
    "think"
    ">",
    flags=re.IGNORECASE | re.DOTALL,
)


class RejectionLlmService:
    def generate_rejection_email(
        self,
        *,
        invoice_number: str,
        rejection_reason: str | None,
        issues: list[str],
        executive_summary: str | None,
    ) -> dict[str, str]:
        if not settings.GROQ_API_KEY:
            raise RejectionDraftGenerationError(
                "GROQ_API_KEY is not configured for rejection draft generation.",
            )

        prompt = self._build_prompt(
            invoice_number=invoice_number,
            rejection_reason=rejection_reason,
            issues=issues,
            executive_summary=executive_summary,
        )
        response_text = self._call_groq(
            prompt,
        )

        try:
            payload = json.loads(
                self._extract_json_text(
                    response_text,
                ),
            )
        except json.JSONDecodeError as error:
            raise RejectionDraftGenerationError(
                "Failed to parse rejection draft from LLM response.",
            ) from error

        subject = str(
            payload.get(
                "subject",
                "",
            ),
        ).strip()
        body = str(
            payload.get(
                "body",
                "",
            ),
        ).strip()

        if not subject or not body:
            raise RejectionDraftGenerationError(
                "LLM returned an incomplete rejection email draft.",
            )

        return {
            "subject": subject,
            "body": body,
        }

    @staticmethod
    def _build_prompt(
        *,
        invoice_number: str,
        rejection_reason: str | None,
        issues: list[str],
        executive_summary: str | None,
    ) -> str:
        issues_text = "\n".join(
            f"- {issue}"
            for issue in issues
        )
        summary_text = executive_summary or "No executive summary available."

        return (
            "You are a finance operations specialist writing a professional "
            "vendor rejection email.\n"
            "Use business-friendly language only.\n"
            "Never expose internal issue codes, database fields, or system "
            "terminology.\n"
            "The email must include:\n"
            "1. Greeting\n"
            "2. Invoice reference\n"
            "3. Review outcome\n"
            "4. Issue summary as bullet points\n"
            "5. Required corrective actions\n"
            "6. Next steps\n"
            "7. Professional closing signed by Finance Team\n\n"
            f"Invoice number: {invoice_number}\n"
            f"Business rejection reason: {rejection_reason or 'Not provided'}\n"
            f"Executive summary: {summary_text}\n"
            f"Issues to communicate:\n{issues_text}\n\n"
            "Return JSON with keys subject and body only. "
            "The body must be plain text with line breaks."
        )

    def _call_groq(
        self,
        prompt: str,
    ) -> str:
        request_body = {
            "model": settings.GROQ_LLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\nReturn valid JSON only."
                    ),
                },
            ],
            "temperature": 0.2,
            "max_tokens": settings.GROQ_LLM_MAX_TOKENS,
            "response_format": {
                "type": "json_object",
            },
        }
        request_data = json.dumps(
            request_body,
        ).encode(
            "utf-8",
        )
        request = urllib.request.Request(
            f"{settings.GROQ_API_BASE_URL.rstrip('/')}/chat/completions",
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=60,
            ) as response:
                response_payload = json.loads(
                    response.read().decode(
                        "utf-8",
                    ),
                )
        except urllib.error.HTTPError as error:
            raise RejectionDraftGenerationError(
                "Failed to generate rejection draft using LLM.",
            ) from error
        except urllib.error.URLError as error:
            raise RejectionDraftGenerationError(
                "Failed to reach LLM provider for rejection draft.",
            ) from error

        return self._extract_chat_completion_text(
            response_payload,
        )

    @staticmethod
    def _extract_chat_completion_text(
        response_payload: dict[str, Any],
    ) -> str:
        choices = response_payload.get(
            "choices",
        )

        if not isinstance(
            choices,
            list,
        ) or not choices:
            raise RejectionDraftGenerationError(
                "LLM response did not include any choices.",
            )

        message = choices[0].get(
            "message",
            {},
        )
        content = message.get(
            "content",
            "",
        )

        if not isinstance(
            content,
            str,
        ) or not content.strip():
            raise RejectionDraftGenerationError(
                "LLM response did not include email content.",
            )

        return content

    @classmethod
    def _extract_json_text(
        cls,
        response_text: str,
    ) -> str:
        stripped_text = _THINKING_BLOCK_PATTERN.sub(
            "",
            response_text,
        ).strip()

        if stripped_text.startswith(
            "{",
        ):
            return stripped_text

        fenced_match = re.search(
            r"```(?:json)?\s*([\s\S]*?)\s*```",
            stripped_text,
        )

        if fenced_match:
            return fenced_match.group(
                1,
            ).strip()

        return stripped_text
