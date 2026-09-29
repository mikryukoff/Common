from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.app.domain.models.user import UserRole


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.USER


class UserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    is_active: bool
    force_password_change: bool


class CreateUserResponse(BaseModel):
    id: int
    username: str
    role: UserRole
    temporary_password: str


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


class UpdateUserActiveRequest(BaseModel):
    is_active: bool


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    details: dict
    timestamp: datetime
