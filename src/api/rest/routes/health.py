"""Health-check route used by deployment and local startup checks."""

from fastapi import (
    APIRouter,
    status,
)
from sqlalchemy import text

from src.data.clients.postgres_client import get_or_create_engine

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Verify that the database connection is reachable."""
    engine = get_or_create_engine()

    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))

    return {"status": "okay"}
