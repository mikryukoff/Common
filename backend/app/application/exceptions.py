"""Прикладные ошибки. Базовые классы — в shared; сюда доменные подклассы."""

from backend.app.shared.exceptions import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    ValidationError,
)

__all__ = [
    "ApplicationError",
    "ConflictError",
    "ForbiddenError",
    "NotFoundError",
    "TooManyRequestsError",
    "UnauthorizedError",
    "UserNotFoundError",
    "UsernameTakenError",
    "ValidationError",
]


class UserNotFoundError(NotFoundError):
    error_code = "user_not_found"

    def __init__(self, user_id: int) -> None:
        super().__init__(
            f"User with id={user_id} not found",
            details={"user_id": user_id},
        )


class UsernameTakenError(ConflictError):
    error_code = "username_taken"

    def __init__(self, username: str) -> None:
        super().__init__(
            f"Username '{username}' is already taken",
            details={"username": username},
        )
