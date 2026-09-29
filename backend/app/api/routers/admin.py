from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_admin_users_service, require_roles
from backend.app.api.schemas.admin import (
    CreateUserRequest,
    CreateUserResponse,
    UpdateUserActiveRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from backend.app.application.admin_users_service import AdminUsersService
from backend.app.domain.models.user import UserRole
from backend.app.infrastructure.db.models.user import UserORM

router = APIRouter(prefix="/admin", tags=["Admin"])
_admin_guard = require_roles([UserRole.ADMIN])


def _to_user_response(user: UserORM) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        force_password_change=user.force_password_change,
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    _: UserORM = Depends(_admin_guard),
    service: AdminUsersService = Depends(get_admin_users_service),
) -> list[UserResponse]:
    users = await service.list_users()
    return [_to_user_response(user) for user in users]


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    payload: CreateUserRequest,
    actor: UserORM = Depends(_admin_guard),
    service: AdminUsersService = Depends(get_admin_users_service),
) -> CreateUserResponse:
    user, temporary = await service.create_user(
        username=payload.username,
        role=payload.role,
        actor_id=actor.id,
    )
    return CreateUserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        temporary_password=temporary,
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    payload: UpdateUserRoleRequest,
    actor: UserORM = Depends(_admin_guard),
    service: AdminUsersService = Depends(get_admin_users_service),
) -> UserResponse:
    user = await service.set_role(user_id=user_id, role=payload.role, actor_id=actor.id)
    return _to_user_response(user)


@router.patch("/users/{user_id}/active", response_model=UserResponse)
async def update_user_active(
    user_id: int,
    payload: UpdateUserActiveRequest,
    actor: UserORM = Depends(_admin_guard),
    service: AdminUsersService = Depends(get_admin_users_service),
) -> UserResponse:
    user = await service.set_active(
        user_id=user_id, is_active=payload.is_active, actor_id=actor.id
    )
    return _to_user_response(user)
