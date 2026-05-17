from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from backend.app.api.auth_deps import admin_user, auth_service, current_user
from backend.app.core.config import settings
from backend.app.models import User
from backend.app.schemas.auth import CreateUserRequest, LoginRequest, LoginResponse, UserRead
from backend.app.schemas.common import MessageResponse


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response) -> LoginResponse:
    if not settings.auth_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth is disabled")
    user, session_token = await auth_service.authenticate(payload.username, payload.password)
    if not user or not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_ttl_hours * 3600,
        path="/",
    )
    return LoginResponse(user=UserRead.model_validate(user))


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    _: User = Depends(current_user),
) -> MessageResponse:
    if session_token:
        await auth_service.revoke_session(session_token)
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.get("/users", response_model=list[UserRead])
async def users(_: User = Depends(admin_user)) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in await auth_service.list_users()]


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: CreateUserRequest, _: User = Depends(admin_user)) -> UserRead:
    try:
        user = await auth_service.create_user(payload.username, payload.password, payload.is_admin)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserRead.model_validate(user)
