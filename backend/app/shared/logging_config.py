from __future__ import annotations

import json
import os
import sys
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import Request
from loguru import logger
from starlette.responses import Response

from backend.app.config import load_config
from backend.app.security.tokens import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    decode_access_token,
    decode_refresh_token,
)
from backend.app.shared.log_redaction import truncate_str
from backend.app.shared.request_log_context import user_log_key_var
from backend.app.shared.user_log_key import format_user_log_key

Logger = type(logger)


def _user_log_key_from_request(request: Request, cfg) -> str:
    def _format_from_payload(payload: dict[str, Any]) -> str:
        uid = int(payload["sub"])
        uname = payload.get("username")
        if isinstance(uname, str) and uname.strip():
            return format_user_log_key(user_id=uid, username=uname)
        return format_user_log_key(user_id=uid, username=None)

    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if token:
        try:
            payload = decode_access_token(token, cfg)
            return _format_from_payload(payload)
        except Exception:
            pass

    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token, cfg)
            return _format_from_payload(payload)
        except Exception:
            pass

    return "unauthenticated"


class StructuredLogger:
    def __init__(self) -> None:
        self.config = load_config()
        self.logger = logger
        self.logs_path = Path(self.config.logger.logs_path)
        self._is_configured = False
        self.request_id_ctx: ContextVar[str] = ContextVar("request_id", default="N/A")
        self.log_body_enabled = os.getenv("LOG_BODY_ENABLED", "false").lower() == "true"
        self.log_verbose_http = os.getenv("LOG_VERBOSE_HTTP", "false").lower() == "true"

    def _append_user_app_line(self, message) -> None:
        rec = message.record
        extra = rec["extra"]
        line = extra.get("serialized")
        if not line:
            return
        key = extra.get("user_log_key", "unauthenticated")
        day = rec["time"].strftime("%Y-%m-%d")
        safe_key = (
            "".join(c if c.isalnum() or c in "._-" else "_" for c in key)[:80]
            or "unauthenticated"
        )
        base = Path(self.config.user_data.base_path) / "users" / safe_key / "logs"
        base.mkdir(parents=True, exist_ok=True)
        fp = base / f"app_{day}.jsonl"
        with fp.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def setup_logger(self) -> None:
        if self._is_configured:
            return

        self.logger.remove()
        self.logger.configure(patcher=self.patching)
        self.logs_path.mkdir(parents=True, exist_ok=True)

        self.logger.add(
            sys.stdout,
            format="{extra[serialized]}",
            level="INFO",
            colorize=True,
            backtrace=False,
            diagnose=False,
        )
        self.logger.add(
            self._append_user_app_line,
            level="DEBUG",
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )

        def security_sink(message) -> None:
            rec = message.record
            line = rec["extra"].get("serialized")
            if line:
                day = rec["time"].strftime("%Y-%m-%d")
                path = self.logs_path / f"security_audit_{day}.jsonl"
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(line + "\n")

        self.logger.add(
            security_sink,
            level="INFO",
            backtrace=False,
            diagnose=False,
            enqueue=True,
            filter=lambda record: record.get("message") == "Security audit event",
        )
        self._is_configured = True

    def serialize(self, record) -> str:
        status_code = record["extra"].get("status_code", "N/A")
        message = record.get("message", "")
        is_request_handled = message == "Request handled"
        is_success_status = isinstance(status_code, int) and status_code < 400
        compact_http = is_request_handled and is_success_status

        log_data = {
            "message": message,
            "timestamp": record["time"].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "level": record["level"].name,
            "request_id": record["extra"].get("request_id", "N/A"),
            "user_log_key": record["extra"].get("user_log_key", "unauthenticated"),
            "method": record["extra"].get("method", "N/A"),
            "path": record["extra"].get("path", "N/A"),
            "status_code": record["extra"].get("status_code", "N/A"),
            "duration_ms": record["extra"].get("duration_ms", "N/A"),
            "error_type": record["extra"].get("error_type", "N/A"),
            "error_message": record["extra"].get("error_message", "N/A"),
        }

        if message == "Security audit event":
            log_data["audit_user_id"] = record["extra"].get("user_id", "N/A")
            log_data["action"] = record["extra"].get("action", "N/A")
            log_data["details"] = record["extra"].get("details", {})

        if compact_http:
            pass
        elif self.log_verbose_http:
            log_data["headers"] = record["extra"].get("headers", {})
            log_data["cookies"] = record["extra"].get("cookies", {})
            log_data["body"] = record["extra"].get("body", "N/A")
            log_data["content_type"] = record["extra"].get("content_type", "N/A")
        elif message == "Request failed":
            log_data["error_message"] = truncate_str(
                str(record["extra"].get("error_message", "")), 500
            )

        return json.dumps(log_data, ensure_ascii=False)

    def patching(self, record) -> None:
        if "request_id" not in record["extra"]:
            record["extra"]["request_id"] = self.request_id_ctx.get()
        record["extra"]["user_log_key"] = user_log_key_var.get()
        record["extra"]["serialized"] = self.serialize(record)

    def set_request_id(self, request_id: str):
        return self.request_id_ctx.set(request_id)

    def reset_request_id(self, token) -> None:
        self.request_id_ctx.reset(token)

    def bind_request(self, request_id: str):
        return self.logger.bind(request_id=request_id)

    async def log_request(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration_ms: float,
    ) -> None:
        self.bind_request(request_id).bind(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        ).info("Request handled")

    async def log_error(
        self,
        request: Request,
        exc: Exception,
        *,
        status_code: int,
        request_id: str,
        duration_ms: float | None = None,
    ) -> None:
        try:
            self.logger.bind(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                headers=self.mask_headers(dict(request.headers)),
                cookies=self.mask_cookies(dict(request.cookies)),
                body=await self.safe_extract_body(request),
                content_type=request.headers.get("content-type", "unknown"),
                status_code=status_code,
                error_type=type(exc).__name__,
                error_message=str(exc),
                duration_ms=duration_ms,
            ).error("Request failed")
        except Exception as log_exc:
            sys.stderr.write(
                f"[LOGGER_FALLBACK] Logging failed: {log_exc} | Original error: {exc}\n"
            )

    async def safe_extract_body(self, request: Request, max_length: int = 2048) -> Any:
        if not self.log_body_enabled:
            return "Body logging disabled"

        try:
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" in content_type:
                form_data = await request.form()
                files_meta = []
                for key, value in form_data.items():
                    if hasattr(value, "filename"):
                        files_meta.append(
                            {
                                "field_name": key,
                                "file_name": value.filename,
                                "content_type": getattr(
                                    value, "content_type", "UNKNOWN"
                                ),
                            }
                        )
                    else:
                        as_text = str(value)
                        files_meta.append(
                            {
                                "field_name": key,
                                "value": as_text[:100],
                            }
                        )
                return files_meta

            body = await request.body()
            if len(body) > max_length:
                return f"Body truncated: {len(body)} bytes"
            if "application/json" in content_type:
                try:
                    return self.mask_sensitive_data(json.loads(body))
                except Exception:
                    return body.decode("utf-8", errors="replace")[:max_length]
            return body.decode("utf-8", errors="replace")[:max_length]
        except Exception as exc:
            return f"Error extracting body: {exc}"

    def mask_headers(self, headers: dict[str, str]) -> dict[str, str]:
        sensitive = {"authorization", "cookie", "set-cookie", "x-api-key"}
        masked: dict[str, str] = {}
        for key, value in headers.items():
            if any(item in key.lower() for item in sensitive):
                masked[key] = "***MASKED***"
            else:
                masked[key] = value
        return masked

    def mask_cookies(self, cookies: dict[str, str]) -> dict[str, str]:
        return {key: "***MASKED***" for key in cookies}

    def mask_sensitive_data(self, data: Any) -> Any:
        sensitive_fields = {"password", "token", "secret", "key"}
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                if any(item in key.lower() for item in sensitive_fields):
                    masked[key] = "***MASKED***"
                else:
                    masked[key] = self.mask_sensitive_data(value)
            return masked
        if isinstance(data, list):
            return [self.mask_sensitive_data(item) for item in data]
        return data

    def make_middleware(self):
        cfg = self.config

        async def logging_middleware(request: Request, call_next):
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            request.state.request_id = request_id
            body = await request.body()

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive
            ukey = _user_log_key_from_request(request, cfg)
            t_user = user_log_key_var.set(ukey)
            token = self.set_request_id(request_id)
            started = time.perf_counter()
            try:
                response = await call_next(request)
                duration_ms = (time.perf_counter() - started) * 1000
                await self.log_request(request, response, request_id, duration_ms)
                response.headers["X-Request-ID"] = request_id
                return response
            except Exception as exc:
                duration_ms = (time.perf_counter() - started) * 1000
                await self.log_error(
                    request,
                    exc,
                    status_code=500,
                    request_id=request_id,
                    duration_ms=duration_ms,
                )
                raise
            finally:
                self.reset_request_id(token)
                user_log_key_var.reset(t_user)

        return logging_middleware


_structured_logger: StructuredLogger | None = None


def get_structured_logger() -> StructuredLogger:
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
    return _structured_logger


def get_logger(name: str | None = None) -> Logger:
    """Единая точка логирования. `name` — обычно `__name__` модуля."""

    log = get_structured_logger().logger
    if name is None:
        return log
    return log.bind(module=name)


def setup_logger() -> None:
    """Настраивает sinks структурированного логгера."""

    get_structured_logger().setup_logger()
