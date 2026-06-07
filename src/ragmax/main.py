from fastapi import FastAPI

from ragmax.api.v1.router import api_router
from ragmax.core.config import get_settings
from ragmax.core.lifespan import lifespan
from ragmax.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
        }

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()

