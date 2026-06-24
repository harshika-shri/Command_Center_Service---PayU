from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.invoice_access_service import (
    InvoiceAccessService,
)
from src.core.services.invoice_extraction_service import (
    InvoiceExtractionService,
)
from src.core.services.invoice_header_service import (
    InvoiceHeaderService,
)
from src.core.services.invoice_validation_detail_service import (
    InvoiceValidationDetailService,
)
from src.core.services.line_allocation_candidate_service import (
    LineAllocationCandidateService,
)
from src.core.services.po_candidate_service import (
    POCandidateService,
)
from src.schemas.invoice_review_schema import (
    InvoiceReviewResponse,
    InvoiceWorkflowState,
)


class InvoiceReviewService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.access_service = InvoiceAccessService(
            session,
        )
        self.header_service = InvoiceHeaderService(
            session,
        )
        self.extraction_service = InvoiceExtractionService(
            session,
        )
        self.validation_service = InvoiceValidationDetailService(
            session,
        )
        self.po_candidate_service = POCandidateService(
            session,
        )
        self.line_allocation_service = LineAllocationCandidateService(
            session,
        )

    async def get_review(
        self,
        invoice_id: UUID,
    ) -> InvoiceReviewResponse:
        await self.access_service.ensure_invoice_exists(
            invoice_id,
        )

        line_allocation_candidates = (
            await self.line_allocation_service.get_line_allocation_candidates(
                invoice_id,
                require_exists=False,
            )
        )
        header = await self.header_service.get_header(
            invoice_id,
            require_exists=False,
        )

        return InvoiceReviewResponse(
            workflow=InvoiceWorkflowState(
                validation_outcome=header.validation_outcome,
                invoice_status=header.invoice_status,
            ),
            header=header,
            extraction=await self.extraction_service.get_extraction(
                invoice_id,
                require_exists=False,
            ),
            validation=await self.validation_service.get_validation(
                invoice_id,
                require_exists=False,
            ),
            po_candidates=await self.po_candidate_service.get_po_candidates(
                invoice_id,
                require_exists=False,
            ),
            line_allocation_candidates=line_allocation_candidates,
        )
