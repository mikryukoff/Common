from collections.abc import Awaitable, Callable
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.application.admin_users_service import AdminUsersService
from backend.app.application.auth_service import AuthService
from backend.app.application.exceptions import ForbiddenError, UnauthorizedError
from backend.app.application.security.audit_service import AuditService
from backend.app.config import Config, load_config
from backend.app.domain.models.user import UserRole
from backend.app.infrastructure.db.database import get_async_session
from backend.app.infrastructure.db.models.user import UserORM
from backend.app.infrastructure.repositories.audit_repository import AuditRepository
from backend.app.infrastructure.repositories.user_repository import UserRepository
from backend.app.security.file_encryption import FileEncryptionService
from backend.app.security.tokens import ACCESS_COOKIE_NAME, decode_access_token


@lru_cache
def get_config() -> Config:
    return load_config()


def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)


def get_audit_repository(
    session: AsyncSession = Depends(get_async_session),
) -> AuditRepository:
    return AuditRepository(session)


def get_audit_service(
    repo: AuditRepository = Depends(get_audit_repository),
) -> AuditService:
    return AuditService(repo=repo)


def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    audit: AuditService = Depends(get_audit_service),
    config: Config = Depends(get_config),
) -> AuthService:
    return AuthService(users=users, audit=audit, config=config)


def get_admin_users_service(
    users: UserRepository = Depends(get_user_repository),
    audit: AuditService = Depends(get_audit_service),
    config: Config = Depends(get_config),
) -> AdminUsersService:
    return AdminUsersService(users=users, audit=audit, config=config)


@lru_cache
def get_file_encryption_service() -> FileEncryptionService:
    return FileEncryptionService(load_config().security.file_encryption_key)


async def get_current_user(
    request: Request,
    config: Config = Depends(get_config),
    users: UserRepository = Depends(get_user_repository),
) -> UserORM:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise UnauthorizedError("Authentication required")

    payload = decode_access_token(token, config)
    user = await users.get_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid user")
    return user


async def get_current_user_optional(
    request: Request,
    config: Config = Depends(get_config),
    users: UserRepository = Depends(get_user_repository),
) -> UserORM | None:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return None
    try:
        payload = decode_access_token(token, config)
    except UnauthorizedError:
        return None
    user = await users.get_by_id(int(payload["sub"]))
    if user is None or not user.is_active:
        return None
    return user


def require_roles(
    roles: list[UserRole],
) -> Callable[..., Awaitable[UserORM]]:
    async def _guard(user: UserORM = Depends(get_current_user)) -> UserORM:
        if user.role not in roles:
            raise ForbiddenError("Insufficient permissions")
        return user

    return _guard
