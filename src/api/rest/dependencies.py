from collections.abc import AsyncGenerator

from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.clients.postgres_client import get_session_factory

# =========================
# Database Dependency
# =========================


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session

            await session.commit()

        except Exception:
            await session.rollback()
            raise


# =========================
# JWT Security
# =========================

security = HTTPBearer(
    auto_error=False,
)
