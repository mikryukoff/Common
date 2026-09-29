from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.db.models.user import UserORM


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> UserORM | None:
        result = await self._session.execute(
            select(UserORM).where(UserORM.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> UserORM | None:
        return await self._session.get(UserORM, user_id)

    async def list_users(self) -> list[UserORM]:
        result = await self._session.execute(select(UserORM).order_by(UserORM.id.asc()))
        return list(result.scalars())

    async def add(self, user: UserORM) -> UserORM:
        self._session.add(user)
        await self._session.flush()
        return user

    async def flush(self) -> None:
        """Сохраняет изменения уже загруженных сущностей в текущей транзакции."""

        await self._session.flush()

    async def commit(self) -> None:
        """Фиксирует текущую транзакцию."""

        await self._session.commit()

    async def rollback(self) -> None:
        """Откатывает текущую транзакцию."""

        await self._session.rollback()
