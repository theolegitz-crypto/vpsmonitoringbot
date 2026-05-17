from fastapi import Cookie, Depends, HTTPException, status

from backend.app.core.config import settings
from backend.app.models import User
from backend.app.db.session import AsyncSessionLocal
from backend.app.services.auth import AuthService


auth_service = AuthService(AsyncSessionLocal)


async def current_user(
    session_token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> User:
    if not settings.auth_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Auth is disabled")
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = await auth_service.get_user_by_token(session_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user


async def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
