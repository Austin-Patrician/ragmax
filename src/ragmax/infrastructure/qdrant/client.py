from qdrant_client import QdrantClient

from ragmax.core.config import Settings, get_settings


def create_qdrant_client(settings: Settings | None = None) -> QdrantClient:
    resolved_settings = settings or get_settings()
    api_key = (
        resolved_settings.qdrant_api_key.get_secret_value()
        if resolved_settings.qdrant_api_key
        else None
    )
    return QdrantClient(url=resolved_settings.qdrant_url, api_key=api_key)

