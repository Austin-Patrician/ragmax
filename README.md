# Ragmax

Ragmax is a FastAPI backend scaffold for a notebook-style RAG system.

## Development

```bash
uv sync
uv run uvicorn ragmax.main:app --reload
```

## Indexing Configuration

Copy `.env.example` to `.env` and fill the service keys needed for your local run.

LlamaParse is registered as an optional file parser. Configure it with:

```env
LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key
LLAMAPARSE_DEFAULT_TIER=agentic
LLAMAPARSE_DEFAULT_VERSION=latest
```

By default, file uploads use `simple_directory_reader`. To make LlamaParse the default parser
for file indexing, set:

```env
DEFAULT_FILE_PARSER=llamaparse
```

You can also keep the default parser and request LlamaParse per indexing call with
`parser_name: "llamaparse"`.
`parser_name` controls parsing only; `profile_name` controls chunking/indexing strategy only.

Vector indexing is off by default. Enable it with:

```env
VECTOR_INDEX_ENABLED=true
VECTOR_SPARSE_INDEX_ENABLED=true
EMBEDDING_PROVIDER=hash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

`EMBEDDING_PROVIDER=hash` uses a local deterministic hash embedding implementation. It is
useful for development and tests because it needs no external service, but it is not a semantic
embedding model and should not be used to judge production retrieval quality.

For OpenAI embeddings, use:

```env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_EMBEDDING_BATCH_SIZE=16
```

Set `OPENAI_BASE_URL` when using an OpenAI-compatible embedding gateway or proxy.
Use the API root such as `https://gateway.example.com/v1`; do not include
`/embeddings`, because the OpenAI client appends that path itself.
If the gateway returns empty embedding data for large indexing jobs, lower
`OPENAI_EMBEDDING_BATCH_SIZE`; start with `8` or `16` and tune upward.

When `VECTOR_SPARSE_INDEX_ENABLED=true`, new Qdrant collections are created with
both the dense vector and the `text-sparse` sparse vector used by BM25 retrieval.
Existing non-empty dense-only collections cannot be upgraded in place by Qdrant;
delete or rebuild the collection, then re-run indexing before enabling BM25.

Hybrid retrieval and BGE fine reranking are controlled with:

```env
RETRIEVAL_ENABLED=true
RETRIEVAL_BM25_ENABLED=true
RETRIEVAL_BM25_TOP_K=100
RETRIEVAL_RERANKING_STAGES=coarse,fine
RETRIEVAL_RERANKER_FINE=bge
RETRIEVAL_RERANKER_FINE_MODEL=BAAI/bge-reranker-v2-m3
RETRIEVAL_RERANKER_FINE_DEVICE=cpu
```

The BGE reranker is loaded lazily on the first fine rerank request. If model
loading or inference fails, `/retrieval/answer` returns a 500 error instead of
falling back silently.

## Checks

```bash
uv run pytest
uv run ruff check .
```
