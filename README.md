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

## Checks

```bash
uv run pytest
uv run ruff check .
```

