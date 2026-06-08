from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ragmax.core.config import get_settings
from ragmax.infrastructure.db.repositories.auth import bootstrap_auth_user
from ragmax.infrastructure.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.auth_bootstrap_username and settings.auth_bootstrap_password is not None:
        await bootstrap_auth_user(
            SessionLocal,
            username=settings.auth_bootstrap_username,
            password=settings.auth_bootstrap_password.get_secret_value(),
            routes=settings.auth_bootstrap_route_list,
        )
    yield
