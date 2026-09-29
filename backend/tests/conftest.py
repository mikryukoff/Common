import os


def _set_default_env(name: str, value: str) -> None:
    if not os.getenv(name):
        os.environ[name] = value


_set_default_env("PROJECT_NAME", "App")
_set_default_env("VERSION", "test")
_set_default_env("ENVIRONMENT", "test")
_set_default_env("DB_HOST", "localhost")
_set_default_env("DB_PORT", "3306")
_set_default_env("DB_NAME", "common_test")
_set_default_env("DB_USER", "test")
_set_default_env("DB_PASSWORD", "test")
_set_default_env("LOGS_OUTPUT_PATH", "data/logs")
_set_default_env("DATA_BASE_PATH", "data")
_set_default_env("UPLOADS_PATH", "data/uploads")
_set_default_env("AUTH_COOKIE_SECURE", "false")
_set_default_env("AUTH_COOKIE_SAMESITE", "lax")
_set_default_env("ALLOW_PASSWORD_GENERATOR_ENDPOINT", "true")
_set_default_env("BOOTSTRAP_ADMIN_RESET_PASSWORD_ON_START", "false")
