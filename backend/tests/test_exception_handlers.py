import asyncio

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from backend.app.api.exception_handlers import register_exception_handlers
from backend.app.application.exceptions import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    UserNotFoundError,
    ValidationError,
)


def _make_request(app: FastAPI, request_id: str = "RID-TEST") -> Request:
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/test",
        "raw_path": b"/test",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "app": app,
    }
    request = Request(scope, receive)
    request.state.request_id = request_id
    return request


def test_application_error_handler_payload() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    handler = app.exception_handlers[ApplicationError]
    request = _make_request(app, request_id="RID-123")

    cases = [
        (ApplicationError("base", details={"x": 1}), 400, "application_error"),
        (NotFoundError("missing"), 404, "not_found"),
        (ConflictError("dup"), 409, "conflict"),
        (ValidationError("bad"), 422, "validation_error"),
        (UnauthorizedError("nope"), 401, "unauthorized"),
        (UserNotFoundError(9), 404, "user_not_found"),
    ]

    for exc, status_code, error_code in cases:
        response = asyncio.run(handler(request, exc))
        payload = response.body.decode("utf-8")
        assert response.status_code == status_code
        assert f'"error":"{error_code}"' in payload
        assert '"request_id":"RID-123"' in payload


def test_request_validation_handler() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    handler = app.exception_handlers[RequestValidationError]
    request = _make_request(app, request_id="RID-VAL")
    exc = RequestValidationError(
        errors=[{"loc": ["query", "value"], "msg": "invalid", "type": "value_error"}]
    )
    response = asyncio.run(handler(request, exc))
    payload = response.body.decode("utf-8")
    assert response.status_code == 422
    assert '"error":"request_validation_error"' in payload


def test_unhandled_exception_handler() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    handler = app.exception_handlers[Exception]
    request = _make_request(app, request_id="RID-500")
    response = asyncio.run(handler(request, RuntimeError("boom")))
    payload = response.body.decode("utf-8")
    assert response.status_code == 500
    assert '"error":"internal_server_error"' in payload
    assert '"request_id":"RID-500"' in payload
