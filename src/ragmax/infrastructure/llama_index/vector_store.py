from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient


def create_text_vector_store(
    client: QdrantClient,
    collection_name: str = "ragmax_text_nodes",
) -> QdrantVectorStore:
    return QdrantVectorStore(client=client, collection_name=collection_name)

