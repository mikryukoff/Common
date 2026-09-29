from types import SimpleNamespace

import pytest

from backend.app.application.exceptions import TooManyRequestsError
from backend.app.security.rate_limit import LoginRateLimiter


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        security=SimpleNamespace(
            login_attempts_limit=2,
            login_window_min=15,
            login_block_min=30,
        )
    )


def test_login_rate_limit_blocks_after_limit() -> None:
    limiter = LoginRateLimiter()
    cfg = _config()
    ip = "127.0.0.1"

    limiter.check(ip=ip, cfg=cfg)
    limiter.mark_failure(ip=ip, cfg=cfg)
    limiter.check(ip=ip, cfg=cfg)
    limiter.mark_failure(ip=ip, cfg=cfg)

    with pytest.raises(TooManyRequestsError):
        limiter.check(ip=ip, cfg=cfg)


def test_login_rate_limit_resets_on_success() -> None:
    limiter = LoginRateLimiter()
    cfg = _config()
    ip = "127.0.0.2"

    limiter.mark_failure(ip=ip, cfg=cfg)
    limiter.mark_success(ip=ip)
    limiter.check(ip=ip, cfg=cfg)
