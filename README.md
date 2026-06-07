# Ragmax

Ragmax is a FastAPI backend scaffold for a notebook-style RAG system.

## Development

```bash
uv sync
uv run uvicorn ragmax.main:app --reload
```

## Checks

```bash
uv run pytest
uv run ruff check .
```

