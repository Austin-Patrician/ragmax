from fastapi import APIRouter

from ragmax.api.v1 import health, indexing, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(indexing.router)
api_router.include_router(sources.router)
