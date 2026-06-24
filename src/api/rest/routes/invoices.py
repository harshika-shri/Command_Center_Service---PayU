from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import (
    get_db_session,
    require_roles,
)
from src.core.services.approve_invoice_service import (
    ApproveInvoiceService,
)
from src.core.services.escalate_invoice_service import (
    EscalateInvoiceService,
)
from src.core.services.invoice_extraction_service import (
    InvoiceExtractionService,
)
from src.core.services.invoice_header_service import (
    InvoiceHeaderService,
)
from src.core.services.invoice_review_service import (
    InvoiceReviewService,
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
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.schemas.approval_schema import (
    ApproveInvoiceRequest,
    ApproveInvoiceResponse,
)
from src.schemas.escalation_schema import (
    EscalateInvoiceRequest,
    EscalateInvoiceResponse,
)
from src.schemas.invoice_review_schema import (
    InvoiceExtractionResponse,
    InvoiceHeaderResponse,
    InvoiceReviewResponse,
    InvoiceValidationResponse,
    LineAllocationCandidateResponse,
    POCandidateResponse,
)

router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"],
)

INVOICE_REVIEW_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
    UserRole.FINANCE_MANAGER,
)

ESCALATION_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
)


@router.get(
    "/{invoice_id}/header",
    response_model=InvoiceHeaderResponse,
)
async def get_invoice_header(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> InvoiceHeaderResponse:
    service = InvoiceHeaderService(
        db,
    )

    return await service.get_header(
        invoice_id,
    )


@router.get(
    "/{invoice_id}/extraction",
    response_model=InvoiceExtractionResponse,
)
async def get_invoice_extraction(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> InvoiceExtractionResponse:
    service = InvoiceExtractionService(
        db,
    )

    return await service.get_extraction(
        invoice_id,
    )


@router.get(
    "/{invoice_id}/validation",
    response_model=InvoiceValidationResponse,
)
async def get_invoice_validation(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> InvoiceValidationResponse:
    service = InvoiceValidationDetailService(
        db,
    )

    return await service.get_validation(
        invoice_id,
    )


@router.get(
    "/{invoice_id}/po-candidates",
    response_model=POCandidateResponse,
)
async def get_invoice_po_candidates(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> POCandidateResponse:
    service = POCandidateService(
        db,
    )

    return await service.get_po_candidates(
        invoice_id,
    )


@router.get(
    "/{invoice_id}/line-allocation-candidates",
    response_model=LineAllocationCandidateResponse,
)
async def get_invoice_line_allocation_candidates(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> LineAllocationCandidateResponse:
    service = LineAllocationCandidateService(
        db,
    )

    return await service.get_line_allocation_candidates(
        invoice_id,
    )


@router.get(
    "/{invoice_id}/review",
    response_model=InvoiceReviewResponse,
)
async def get_invoice_review(
    invoice_id: UUID,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    _: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> InvoiceReviewResponse:
    service = InvoiceReviewService(
        db,
    )

    return await service.get_review(
        invoice_id,
    )


@router.post(
    "/{invoice_id}/approve",
    response_model=ApproveInvoiceResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_invoice(
    invoice_id: UUID,
    request: ApproveInvoiceRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *INVOICE_REVIEW_ROLES,
        ),
    ),
) -> ApproveInvoiceResponse:
    if request.approved_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="approved_by must match the authenticated user.",
        )

    service = ApproveInvoiceService(
        db,
    )

    return await service.approve_invoice(
        invoice_id,
        request,
    )


@router.post(
    "/{invoice_id}/escalate",
    response_model=EscalateInvoiceResponse,
    status_code=status.HTTP_200_OK,
)
async def escalate_invoice(
    invoice_id: UUID,
    request: EscalateInvoiceRequest,
    db: AsyncSession = Depends(
        get_db_session,
    ),
    current_user: User = Depends(
        require_roles(
            *ESCALATION_ROLES,
        ),
    ),
) -> EscalateInvoiceResponse:
    if request.escalated_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="escalated_by must match the authenticated user.",
        )

    service = EscalateInvoiceService(
        db,
    )

    return await service.escalate_invoice(
        invoice_id,
        request,
    )
