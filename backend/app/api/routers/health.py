from fastapi import APIRouter

from backend.app.api.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness-проверка для Docker HEALTHCHECK."""

    return HealthResponse(status="ok")
