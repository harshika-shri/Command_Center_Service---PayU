from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.rest.dependencies import get_db_session, require_roles
from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.data.repositories.user_repo import UserRepository
from src.schemas.user_schema import ManagerSummary

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

_CALLER_ROLES = (
    UserRole.FINANCE_ASSOCIATE,
    UserRole.FINANCE_MANAGER,
)


@router.get(
    "/managers",
    response_model=list[ManagerSummary],
)
async def list_finance_managers(
    db: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_roles(*_CALLER_ROLES)),
) -> list[ManagerSummary]:
    repo = UserRepository(db)
    managers = await repo.list_managers()
    return [
        ManagerSummary(id=str(m.id), name=m.name, email=m.email)
        for m in managers
    ]
