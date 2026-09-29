from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from backend.app.domain.models.user import UserRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=255)
    current_password: str | None = None
    change_password_token: str | None = None

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str) -> str:
        if not any(ch.islower() for ch in value):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not any(ch.isupper() for ch in value):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(ch in "!@#$%^&*()-_=+[]{};:,.<>?/\\|" for ch in value):
            raise ValueError("Пароль должен содержать хотя бы один спецсимвол")
        return value


class OkResponse(BaseModel):
    ok: bool = True


class RefreshResponse(OkResponse):
    pass


class LoginSuccessResponse(BaseModel):
    ok: bool = True
    user_id: int
    role: UserRole


class ForcePasswordResponse(BaseModel):
    error: str = "force_password_change"
    change_password_token: str


class MeResponse(BaseModel):
    user_id: int
    username: str
    role: UserRole
    is_active: bool


class ChangePasswordResponse(BaseModel):
    ok: bool = True
    require_relogin: bool


class GeneratePasswordResponse(BaseModel):
    password: str
