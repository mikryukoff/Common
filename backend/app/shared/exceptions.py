"""Базовые прикладные ошибки без привязки к HTTP-фреймворку."""


class ApplicationError(Exception):
    """Базовая ошибка приложения со стабильным кодом."""

    status_code = 400
    error_code = "application_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(ApplicationError):
    status_code = 404
    error_code = "not_found"


class ConflictError(ApplicationError):
    status_code = 409
    error_code = "conflict"


class ValidationError(ApplicationError):
    status_code = 422
    error_code = "validation_error"


class UnauthorizedError(ApplicationError):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(ApplicationError):
    status_code = 403
    error_code = "forbidden"


class TooManyRequestsError(ApplicationError):
    status_code = 429
    error_code = "too_many_requests"
