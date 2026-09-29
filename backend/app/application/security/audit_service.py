from __future__ import annotations

from backend.app.infrastructure.repositories.audit_repository import AuditRepository
from backend.app.shared.logging_config import get_logger


class AuditService:
    """Пишет аудит в БД и в security-лог."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def log(
        self,
        *,
        user_id: int | None,
        action: str,
        details: dict | None = None,
    ) -> None:
        safe_details = details or {}
        await self.repo.create(user_id=user_id, action=action, details=safe_details)
        get_logger().bind(user_id=user_id, action=action, details=safe_details).info(
            "Security audit event"
        )
