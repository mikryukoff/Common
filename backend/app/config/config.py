from dataclasses import dataclass

from environs import Env


@dataclass(frozen=True, slots=True)
class App:
    """Метаданные приложения из окружения."""

    project_name: str
    version: str
    environment: str


@dataclass(frozen=True, slots=True)
class Database:
    """Параметры подключения к MySQL."""

    host: str
    user: str
    password: str
    db_name: str
    db_port: str


@dataclass(frozen=True, slots=True)
class Logger:
    """Каталог файловых логов."""

    logs_path: str


@dataclass(frozen=True, slots=True)
class UserData:
    """Корень рабочих данных (логи пользователей, загрузки)."""

    base_path: str
    uploads_path: str


@dataclass(frozen=True, slots=True)
class Security:
    """Секреты JWT, cookies и bootstrap-админа."""

    jwt_access_secret: str
    jwt_refresh_secret: str
    jwt_change_password_secret: str
    jwt_access_ttl_min: int
    jwt_refresh_ttl_days: int
    jwt_change_password_ttl_min: int
    file_encryption_key: str
    temp_password_len: int
    login_attempts_limit: int
    login_window_min: int
    login_block_min: int
    auth_cookie_secure: bool
    auth_cookie_samesite: str
    allow_password_generator_endpoint: bool
    bootstrap_admin_username: str
    bootstrap_admin_password: str
    bootstrap_admin_role: str
    bootstrap_admin_is_active: bool
    bootstrap_admin_reset_password_on_start: bool
    force_relogin_on_restart: bool


@dataclass(frozen=True, slots=True)
class Config:
    """Корневая конфигурация приложения."""

    app: App
    database: Database
    logger: Logger
    user_data: UserData
    security: Security


_DEFAULT_SECRET_VALUES = {
    "JWT_ACCESS_SECRET": "change-me-access-secret",
    "JWT_REFRESH_SECRET": "change-me-refresh-secret",
    "JWT_CHANGE_PASSWORD_SECRET": "change-me-change-password-secret",
    "FILE_ENCRYPTION_KEY": "insecure-dev-key",
    "BOOTSTRAP_ADMIN_PASSWORD": "admin12345!",
}


def _is_production_environment(environment: str) -> bool:
    env = (environment or "").strip().lower()
    return env in {"prod", "production"}


def _validate_prod_security(config: Config) -> None:
    if not _is_production_environment(config.app.environment):
        return

    secret_checks = {
        "JWT_ACCESS_SECRET": config.security.jwt_access_secret,
        "JWT_REFRESH_SECRET": config.security.jwt_refresh_secret,
        "JWT_CHANGE_PASSWORD_SECRET": config.security.jwt_change_password_secret,
        "FILE_ENCRYPTION_KEY": config.security.file_encryption_key,
        "BOOTSTRAP_ADMIN_PASSWORD": config.security.bootstrap_admin_password,
    }
    weak_vars = [
        key
        for key, value in secret_checks.items()
        if value == _DEFAULT_SECRET_VALUES[key]
    ]
    if weak_vars:
        joined = ", ".join(sorted(weak_vars))
        raise ValueError(
            f"Production startup blocked: insecure default secrets detected ({joined})."
        )

    if config.security.bootstrap_admin_reset_password_on_start:
        raise ValueError(
            "Production startup blocked: "
            "BOOTSTRAP_ADMIN_RESET_PASSWORD_ON_START must be false."
        )
    if not config.security.auth_cookie_secure:
        raise ValueError("Production startup blocked: AUTH_COOKIE_SECURE must be true.")
    if config.security.auth_cookie_samesite not in {"lax", "strict", "none"}:
        raise ValueError(
            "Production startup blocked: AUTH_COOKIE_SAMESITE must be one of "
            "lax/strict/none."
        )
    if (
        config.security.auth_cookie_samesite == "none"
        and not config.security.auth_cookie_secure
    ):
        raise ValueError(
            "Production startup blocked: AUTH_COOKIE_SAMESITE=none requires "
            "AUTH_COOKIE_SECURE=true."
        )


def load_config(path: str | None = None) -> Config:
    """Читает `.env` и собирает типизированный конфиг."""

    env = Env()
    env.read_env(path)

    app_environment = env("ENVIRONMENT", "production").strip().lower() or ("production")
    is_production = _is_production_environment(app_environment)

    auth_cookie_secure = env.bool("AUTH_COOKIE_SECURE", is_production)
    auth_cookie_samesite = (
        env("AUTH_COOKIE_SAMESITE", "strict" if is_production else "lax")
        .strip()
        .lower()
    )
    allow_password_generator_endpoint = env.bool(
        "ALLOW_PASSWORD_GENERATOR_ENDPOINT",
        not is_production,
    )

    config = Config(
        app=App(
            project_name=env("PROJECT_NAME", "common"),
            version=env("VERSION", "0.1.0"),
            environment=app_environment,
        ),
        database=Database(
            host=env("DB_HOST"),
            user=env("DB_USER"),
            password=env("DB_PASSWORD"),
            db_name=env("DB_NAME"),
            db_port=env("DB_PORT"),
        ),
        logger=Logger(logs_path=env("LOGS_OUTPUT_PATH", "data/logs")),
        user_data=UserData(
            base_path=env("DATA_BASE_PATH", "data"),
            uploads_path=env("UPLOADS_PATH", "data/uploads"),
        ),
        security=Security(
            jwt_access_secret=env(
                "JWT_ACCESS_SECRET",
                _DEFAULT_SECRET_VALUES["JWT_ACCESS_SECRET"],
            ),
            jwt_refresh_secret=env(
                "JWT_REFRESH_SECRET",
                _DEFAULT_SECRET_VALUES["JWT_REFRESH_SECRET"],
            ),
            jwt_change_password_secret=env(
                "JWT_CHANGE_PASSWORD_SECRET",
                _DEFAULT_SECRET_VALUES["JWT_CHANGE_PASSWORD_SECRET"],
            ),
            jwt_access_ttl_min=env.int("JWT_ACCESS_TTL_MIN", 15),
            jwt_refresh_ttl_days=env.int("JWT_REFRESH_TTL_DAYS", 7),
            jwt_change_password_ttl_min=env.int("JWT_CHANGE_PASSWORD_TTL_MIN", 10),
            file_encryption_key=env(
                "FILE_ENCRYPTION_KEY",
                _DEFAULT_SECRET_VALUES["FILE_ENCRYPTION_KEY"],
            ),
            temp_password_len=env.int("TEMP_PASSWORD_LEN", 12),
            login_attempts_limit=env.int("LOGIN_ATTEMPTS_LIMIT", 5),
            login_window_min=env.int("LOGIN_WINDOW_MIN", 15),
            login_block_min=env.int("LOGIN_BLOCK_MIN", 30),
            auth_cookie_secure=auth_cookie_secure,
            auth_cookie_samesite=auth_cookie_samesite,
            allow_password_generator_endpoint=(allow_password_generator_endpoint),
            bootstrap_admin_username=env("BOOTSTRAP_ADMIN_USERNAME", "admin"),
            bootstrap_admin_password=env(
                "BOOTSTRAP_ADMIN_PASSWORD",
                _DEFAULT_SECRET_VALUES["BOOTSTRAP_ADMIN_PASSWORD"],
            ),
            bootstrap_admin_role=env("BOOTSTRAP_ADMIN_ROLE", "admin"),
            bootstrap_admin_is_active=env.bool("BOOTSTRAP_ADMIN_IS_ACTIVE", True),
            bootstrap_admin_reset_password_on_start=env.bool(
                "BOOTSTRAP_ADMIN_RESET_PASSWORD_ON_START",
                False if is_production else True,
            ),
            force_relogin_on_restart=env.bool("FORCE_RELOGIN_ON_RESTART", True),
        ),
    )
    _validate_prod_security(config)
    return config
