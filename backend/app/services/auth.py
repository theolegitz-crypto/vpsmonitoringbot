import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.models import AuthSession, User


PBKDF2_ITERATIONS = 390000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(derived_key).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_encoded, digest_encoded = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    salt = base64.urlsafe_b64decode(salt_encoded.encode("ascii"))
    expected_digest = base64.urlsafe_b64decode(digest_encoded.encode("ascii"))
    calculated_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, int(iterations)
    )
    return hmac.compare_digest(expected_digest, calculated_digest)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def ensure_bootstrap_admin(self) -> None:
        if not settings.auth_enabled:
            return

        async with self.session_factory() as session:
            any_user = await session.scalar(select(User.id).limit(1))
            if any_user:
                return

            if (
                not settings.auth_bootstrap_username
                or not settings.auth_bootstrap_password
                or settings.auth_bootstrap_password == "change_me_now"
            ):
                raise RuntimeError(
                    "AUTH_BOOTSTRAP_USERNAME and AUTH_BOOTSTRAP_PASSWORD must be set to non-placeholder values before first startup."
                )

            session.add(
                User(
                    username=settings.auth_bootstrap_username,
                    password_hash=hash_password(settings.auth_bootstrap_password),
                    is_admin=True,
                    is_active=True,
                )
            )
            await session.commit()

    async def authenticate(self, username: str, password: str) -> tuple[User | None, str | None]:
        async with self.session_factory() as session:
            user = await session.scalar(select(User).where(User.username == username))
            if not user or not user.is_active or not verify_password(password, user.password_hash):
                return None, None

            token = secrets.token_urlsafe(48)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.auth_session_ttl_hours)

            session.add(
                AuthSession(
                    user_id=user.id,
                    token_hash=hash_session_token(token),
                    expires_at=expires_at,
                    last_seen_at=datetime.now(timezone.utc),
                )
            )
            user.last_login_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(user)
            return user, token

    async def get_user_by_token(self, token: str) -> User | None:
        async with self.session_factory() as session:
            await self._delete_expired_sessions(session)
            auth_session = await session.scalar(
                select(AuthSession)
                .options(selectinload(AuthSession.user))
                .where(AuthSession.token_hash == hash_session_token(token))
            )
            if not auth_session:
                return None
            if auth_session.expires_at <= datetime.now(timezone.utc):
                await session.delete(auth_session)
                await session.commit()
                return None
            auth_session.last_seen_at = datetime.now(timezone.utc)
            await session.commit()
            return auth_session.user if auth_session.user.is_active else None

    async def revoke_session(self, token: str) -> None:
        async with self.session_factory() as session:
            auth_session = await session.scalar(
                select(AuthSession).where(AuthSession.token_hash == hash_session_token(token))
            )
            if auth_session:
                await session.delete(auth_session)
                await session.commit()

    async def list_users(self) -> list[User]:
        async with self.session_factory() as session:
            users = (await session.scalars(select(User).order_by(User.username.asc()))).all()
            return list(users)

    async def create_user(self, username: str, password: str, is_admin: bool) -> User:
        async with self.session_factory() as session:
            existing = await session.scalar(select(User).where(User.username == username))
            if existing:
                raise ValueError("User with this username already exists")

            user = User(
                username=username,
                password_hash=hash_password(password),
                is_admin=is_admin,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def _delete_expired_sessions(self, session: AsyncSession) -> None:
        await session.execute(
            delete(AuthSession).where(AuthSession.expires_at <= datetime.now(timezone.utc))
        )
        await session.commit()
