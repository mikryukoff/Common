from __future__ import annotations

from backend.app.application.exceptions import (
    UsernameTakenError,
    UserNotFoundError,
)
from backend.app.application.security.audit_service import AuditService
from backend.app.config import Config
from backend.app.domain.models.user import UserRole
from backend.app.infrastructure.db.models.user import UserORM
from backend.app.infrastructure.repositories.user_repository import UserRepository
from backend.app.security.passwords import generate_temporary_password, hash_password


class AdminUsersService:
    """Администрирование учётных записей."""

    def __init__(
        self,
        *,
        users: UserRepository,
        audit: AuditService,
        config: Config,
    ) -> None:
        self.users = users
        self.audit = audit
        self.config = config

    async def list_users(self) -> list[UserORM]:
        return await self.users.list_users()

    async def create_user(
        self,
        *,
        username: str,
        role: UserRole,
        actor_id: int,
    ) -> tuple[UserORM, str]:
        existing = await self.users.get_by_username(username)
        if existing is not None:
            raise UsernameTakenError(username)

        temporary = generate_temporary_password(self.config.security.temp_password_len)
        user = UserORM(
            username=username,
            role=role,
            password_hash=hash_password(temporary),
            temporary_password=temporary,
            force_password_change=True,
            is_active=True,
        )
        await self.users.add(user)
        await self.audit.log(
            user_id=actor_id,
            action="user_created",
            details={"username": username, "role": role.value},
        )
        return user, temporary

    async def set_role(self, *, user_id: int, role: UserRole, actor_id: int) -> UserORM:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        user.role = role
        await self.users.flush()
        await self.audit.log(
            user_id=actor_id,
            action="user_role_updated",
            details={"target_user_id": user_id, "role": role.value},
        )
        return user

    async def set_active(
        self, *, user_id: int, is_active: bool, actor_id: int
    ) -> UserORM:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        user.is_active = is_active
        await self.users.flush()
        await self.audit.log(
            user_id=actor_id,
            action="user_active_updated",
            details={"target_user_id": user_id, "is_active": is_active},
        )
        return user
