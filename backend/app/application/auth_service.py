from __future__ import annotations

from dataclasses import dataclass
from time import time

from backend.app.application.exceptions import UnauthorizedError
from backend.app.application.security.audit_service import AuditService
from backend.app.config import Config
from backend.app.infrastructure.db.models.user import UserORM
from backend.app.infrastructure.repositories.user_repository import UserRepository
from backend.app.security.passwords import hash_password, verify_password
from backend.app.security.rate_limit import login_rate_limiter
from backend.app.security.tokens import (
    create_access_token,
    create_change_password_token,
    create_refresh_token,
    decode_change_password_token,
    decode_refresh_token,
)
from backend.app.shared.logging_config import get_logger

_used_change_password_jti: dict[str, int] = {}


@dataclass(frozen=True, slots=True)
class AuthTokens:
    """Пара access/refresh токенов для установки cookies в api-слое."""

    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class ForcePasswordChange:
    """Логин успешен, но нужна смена временного пароля."""

    token: str


@dataclass(frozen=True, slots=True)
class LoginSuccess:
    """Успешный логин с токенами сессии."""

    user: UserORM
    tokens: AuthTokens


class AuthService:
    """Оркестрация логина, refresh и смены пароля."""

    def __init__(
        self,
        *,
        users: UserRepository,
        audit: AuditService,
        config: Config,
    ) -> None:
        self.users = users
        self.audit = audit
        self.config = config

    async def _safe_audit(
        self,
        *,
        user_id: int | None,
        action: str,
        details: dict | None = None,
    ) -> None:
        try:
            await self.audit.log(user_id=user_id, action=action, details=details or {})
        except Exception:
            get_logger().exception(
                "Audit log write failed. action={} user_id={}", action, user_id
            )

    def _issue_tokens(self, user: UserORM) -> AuthTokens:
        return AuthTokens(
            access_token=create_access_token(
                user.id,
                user.role.value,
                self.config,
                username=user.username,
            ),
            refresh_token=create_refresh_token(
                user.id,
                user.role.value,
                self.config,
                username=user.username,
            ),
        )

    async def login(
        self,
        *,
        username: str,
        password: str,
        ip: str,
    ) -> LoginSuccess | ForcePasswordChange:
        log = get_logger()
        log.info("Login attempt. username={} ip={}", username, ip)
        login_rate_limiter.check(ip=ip, cfg=self.config)

        user = await self.users.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            log.warning(
                "Login failed: invalid credentials. username={} ip={}",
                username,
                ip,
            )
            login_rate_limiter.mark_failure(ip=ip, cfg=self.config)
            await self._safe_audit(
                user_id=user.id if user else None,
                action="login_failed",
                details={"username": username, "ip": ip},
            )
            raise UnauthorizedError("Invalid credentials")
        if not user.is_active:
            log.warning(
                "Login failed: user inactive. username={} user_id={} ip={}",
                username,
                user.id,
                ip,
            )
            login_rate_limiter.mark_failure(ip=ip, cfg=self.config)
            await self._safe_audit(
                user_id=user.id,
                action="login_failed_inactive",
                details={"ip": ip},
            )
            raise UnauthorizedError("User is inactive")

        if user.force_password_change:
            token = create_change_password_token(user.id, self.config)
            await self._safe_audit(
                user_id=user.id,
                action="login_force_password_change",
                details={"ip": ip},
            )
            return ForcePasswordChange(token=token)

        login_rate_limiter.mark_success(ip=ip)
        tokens = self._issue_tokens(user)
        await self._safe_audit(
            user_id=user.id, action="login_success", details={"ip": ip}
        )
        log.info(
            "Login success. username={} user_id={} role={} ip={}",
            username,
            user.id,
            user.role.value,
            ip,
        )
        return LoginSuccess(user=user, tokens=tokens)

    async def refresh(self, *, refresh_token: str) -> AuthTokens:
        payload = decode_refresh_token(refresh_token, self.config)
        user = await self.users.get_by_id(int(payload["sub"]))
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid user")
        return self._issue_tokens(user)

    async def change_password(
        self,
        *,
        new_password: str,
        current_password: str | None,
        change_password_token: str | None,
        current_user: UserORM | None,
    ) -> bool:
        """Меняет пароль. True — нужна повторная авторизация (token-flow)."""

        user: UserORM | None = None
        if change_password_token:
            token_payload = decode_change_password_token(
                change_password_token, self.config
            )
            jti = str(token_payload["jti"])
            exp = int(token_payload.get("exp") or 0)
            _register_change_password_jti_once(jti=jti, exp=exp)
            user = await self.users.get_by_id(int(token_payload["sub"]))
        else:
            user = current_user
            if user is None:
                raise UnauthorizedError("Authentication required")
            if not current_password or not verify_password(
                current_password, user.password_hash
            ):
                raise UnauthorizedError("Current password is invalid")

        if user is None:
            raise UnauthorizedError("User not found")

        user.password_hash = hash_password(new_password)
        user.force_password_change = False
        user.temporary_password = None
        await self.users.flush()
        await self._safe_audit(user_id=user.id, action="password_changed")
        return bool(change_password_token)


def _register_change_password_jti_once(*, jti: str, exp: int) -> None:
    now = int(time())
    expired = [
        token_id
        for token_id, token_exp in _used_change_password_jti.items()
        if token_exp <= now
    ]
    for token_id in expired:
        _used_change_password_jti.pop(token_id, None)

    if (_used_change_password_jti.get(jti) or 0) > now:
        raise UnauthorizedError("Password change token is already used")
    _used_change_password_jti[jti] = max(exp, now + 1)
