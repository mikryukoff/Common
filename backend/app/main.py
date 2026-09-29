from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.exception_handlers import register_exception_handlers
from backend.app.api.routers.admin import router as admin_router
from backend.app.api.routers.auth import router as auth_router
from backend.app.api.routers.health import router as health_router
from backend.app.application.security.bootstrap_admin import ensure_admin_user_from_env
from backend.app.config import load_config
from backend.app.shared.logging_config import (
    get_logger,
    get_structured_logger,
    setup_logger,
)

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logger()
    log = get_logger()
    await ensure_admin_user_from_env()
    log.info("App startup completed. frontend_dir={}", FRONTEND_DIR)
    yield
    log.info("App shutdown")


def create_app() -> FastAPI:
    config = load_config()
    application = FastAPI(
        title=config.app.project_name,
        version=config.app.version,
        lifespan=lifespan,
    )

    def _is_frontend_static_path(path: str) -> bool:
        if path in {"/", "/index.html"}:
            return True
        if path.startswith("/js/") or path.startswith("/css/"):
            return True
        return path.endswith(".html")

    @application.middleware("http")
    async def frontend_cache_control_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        if request.method in {"GET", "HEAD"} and _is_frontend_static_path(
            request.url.path
        ):
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @application.middleware("http")
    async def structured_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        middleware = getattr(application.state, "_structured_logging_middleware", None)
        if middleware is None:
            middleware = get_structured_logger().make_middleware()
            application.state._structured_logging_middleware = middleware
        return await middleware(request, call_next)

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(admin_router)

    @application.get("/favicon.svg")
    async def favicon_svg() -> FileResponse:
        path = FRONTEND_DIR / "favicon.svg"
        if not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(
            path,
            media_type="image/svg+xml",
            headers={"Cache-Control": "no-store"},
        )

    if FRONTEND_DIR.is_dir():
        application.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
        application.mount(
            "/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css"
        )
        application.mount(
            "/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend"
        )
    return application


app = create_app()
