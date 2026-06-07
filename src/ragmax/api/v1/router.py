from fastapi import APIRouter

from ragmax.api.v1 import health, indexing, retrieval, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(indexing.router)
api_router.include_router(retrieval.router)
api_router.include_router(sources.router)
