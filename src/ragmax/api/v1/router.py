from fastapi import APIRouter

from ragmax.api.v1 import (
    auth,
    datasets,
    evaluation,
    health,
    indexing,
    retrieval,
    sources,
    user_settings,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(datasets.router)
api_router.include_router(evaluation.router)
api_router.include_router(health.router)
api_router.include_router(indexing.router)
api_router.include_router(retrieval.router)
api_router.include_router(sources.router)
api_router.include_router(user_settings.router)
