"""Контекст HTTP-запроса для разнесения логов по пользователям."""

from contextvars import ContextVar

user_log_key_var: ContextVar[str] = ContextVar(
    "user_log_key", default="unauthenticated"
)


def get_user_log_key() -> str:
    return user_log_key_var.get()
