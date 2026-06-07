from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ragmax.core.config import Settings, get_settings


def create_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    resolved_settings = settings or get_settings()
    engine = create_async_engine(resolved_settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


SessionLocal = create_session_factory()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

