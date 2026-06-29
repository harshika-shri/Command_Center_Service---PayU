from typing import cast
from uuid import UUID

from sqlalchemy import select

from src.data.models.postgres.enums import UserRole
from src.data.models.postgres.users import User
from src.data.repositories.base_repo import BaseRepository


class UserRepository(BaseRepository):
    async def get_user_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        stmt = select(User).where(
            User.id == user_id,
        )

        result = await self.execute(
            stmt,
        )

        return cast(
            User | None,
            result.scalar_one_or_none(),
        )

    async def list_managers(self) -> list[User]:
        stmt = (
            select(User)
            .where(
                User.role == UserRole.FINANCE_MANAGER,
                User.is_active.is_(True),
            )
            .order_by(User.name)
        )
        result = await self.execute(stmt)
        return list(result.scalars().all())
