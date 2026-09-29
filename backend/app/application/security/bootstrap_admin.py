from __future__ import annotations

from backend.app.config import load_config
from backend.app.domain.models.user import UserRole
from backend.app.infrastructure.db.database import get_session_factory
from backend.app.infrastructure.db.models.user import UserORM
from backend.app.infrastructure.repositories.user_repository import UserRepository
from backend.app.security.passwords import hash_password
from backend.app.shared.logging_config import get_logger


async def ensure_admin_user_from_env() -> None:
    """Создаёт или обновляет bootstrap-админа из переменных окружения."""

    cfg = load_config()
    username = (cfg.security.bootstrap_admin_username or "").strip()
    password = cfg.security.bootstrap_admin_password or ""
    log = get_logger(__name__)
    if not username or not password:
        log.warning(
            "Admin bootstrap skipped: BOOTSTRAP_ADMIN_USERNAME/PASSWORD are empty"
        )
        return

    try:
        role = UserRole(cfg.security.bootstrap_admin_role)
    except ValueError:
        log.warning(
            "Invalid BOOTSTRAP_ADMIN_ROLE='{}', fallback to admin",
            cfg.security.bootstrap_admin_role,
        )
        role = UserRole.ADMIN

    factory = get_session_factory()
    async with factory() as session:
        users = UserRepository(session)
        try:
            user = await users.get_by_username(username)
            if user is None:
                await users.add(
                    UserORM(
                        username=username,
                        role=role,
                        password_hash=hash_password(password),
                        temporary_password=None,
                        force_password_change=False,
                        is_active=cfg.security.bootstrap_admin_is_active,
                    )
                )
                await users.commit()
                log.info(
                    "Bootstrap admin created. username={} role={}",
                    username,
                    role.value,
                )
                return

            user.role = role
            user.is_active = cfg.security.bootstrap_admin_is_active
            user.force_password_change = False
            user.temporary_password = None
            if cfg.security.bootstrap_admin_reset_password_on_start:
                user.password_hash = hash_password(password)
            await users.flush()
            await users.commit()
            log.info(
                "Bootstrap admin updated. username={} role={} "
                "reset_password_on_start={}",
                username,
                role.value,
                cfg.security.bootstrap_admin_reset_password_on_start,
            )
        except Exception:
            await users.rollback()
            log.exception("Failed to bootstrap admin user from env")
