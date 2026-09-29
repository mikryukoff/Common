from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.db.models.audit_log import AuditLogORM


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: int | None,
        action: str,
        details: dict | None = None,
    ) -> AuditLogORM:
        row = AuditLogORM(
            user_id=user_id,
            action=action,
            details=details or {},
            timestamp=datetime.now(tz=UTC).replace(tzinfo=None),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_recent(self, *, limit: int = 100) -> list[AuditLogORM]:
        result = await self._session.execute(
            select(AuditLogORM).order_by(AuditLogORM.timestamp.desc()).limit(limit)
        )
        return list(result.scalars())
