from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from backend.app.api.dependencies import (
    get_auth_service,
    get_config,
    get_current_user,
    get_current_user_optional,
    require_roles,
)
from backend.app.api.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForcePasswordResponse,
    GeneratePasswordResponse,
    LoginRequest,
    LoginSuccessResponse,
    MeResponse,
    OkResponse,
    RefreshResponse,
)
from backend.app.application.auth_service import (
    AuthService,
    ForcePasswordChange,
    LoginSuccess,
)
from backend.app.application.exceptions import ForbiddenError, UnauthorizedError
from backend.app.config import Config
from backend.app.domain.models.user import UserRole
from backend.app.infrastructure.db.models.user import UserORM
from backend.app.security.passwords import generate_temporary_password
from backend.app.security.tokens import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    set_auth_cookies,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginSuccessResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    auth: AuthService = Depends(get_auth_service),
) -> LoginSuccessResponse | JSONResponse:
    ip = request.client.host if request.client else "unknown"
    result = await auth.login(
        username=payload.username,
        password=payload.password,
        ip=ip,
    )
    if isinstance(result, ForcePasswordChange):
        force_response = JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ForcePasswordResponse(
                change_password_token=result.token
            ).model_dump(),
        )
        clear_auth_cookies(force_response, cfg=auth.config)
        return force_response

    assert isinstance(result, LoginSuccess)
    set_auth_cookies(
        response,
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        cfg=auth.config,
    )
    return LoginSuccessResponse(user_id=result.user.id, role=result.user.role)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
) -> RefreshResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise UnauthorizedError("Refresh token is required")
    tokens = await auth.refresh(refresh_token=refresh_token)
    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        cfg=auth.config,
    )
    return RefreshResponse()


@router.post("/logout", response_model=OkResponse)
async def logout(
    response: Response, config: Config = Depends(get_config)
) -> OkResponse:
    clear_auth_cookies(response, cfg=config)
    return OkResponse()


@router.get("/me", response_model=MeResponse)
async def me(current_user: UserORM = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
    current_user: UserORM | None = Depends(get_current_user_optional),
) -> ChangePasswordResponse:
    require_relogin = await auth.change_password(
        new_password=payload.new_password,
        current_password=payload.current_password,
        change_password_token=payload.change_password_token,
        current_user=current_user,
    )
    if require_relogin:
        clear_auth_cookies(response, cfg=auth.config)
    return ChangePasswordResponse(require_relogin=require_relogin)


@router.get("/generate-password", response_model=GeneratePasswordResponse)
async def generate_password(
    config: Config = Depends(get_config),
    _: UserORM = Depends(require_roles([UserRole.ADMIN])),
) -> GeneratePasswordResponse:
    if not config.security.allow_password_generator_endpoint:
        raise ForbiddenError("Password generator endpoint is disabled")
    return GeneratePasswordResponse(
        password=generate_temporary_password(config.security.temp_password_len)
    )
