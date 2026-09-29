"""Чистая модель пользователя без I/O и фреймворков."""

from dataclasses import dataclass
from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


@dataclass(frozen=True, slots=True)
class User:
    """Пользователь предметной области."""

    id: int
    username: str
    role: UserRole
    is_active: bool
    force_password_change: bool
