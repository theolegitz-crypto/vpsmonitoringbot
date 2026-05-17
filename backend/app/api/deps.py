from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session
