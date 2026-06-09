from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ragmax.core.config import Settings
from ragmax.core.exceptions import InvalidRequestError, NotFoundError
from ragmax.infrastructure.db.models import (
    AppRuntimeConfigurationModel,
    ModelDefaultBindingModel,
    ModelProviderModel,
    ProviderModelModel,
)

GLOBAL_CONFIG_ID = "global"
MODEL_BINDING_KEYS = {"answer_llm", "query_llm", "embedding", "rerank"}
MODEL_AI_TYPES = {"llm", "embedding", "rerank", "vlm", "asr", "tts", "ocr", "moderation"}
MODEL_PROVIDER_TYPES = {"openai_compatible", "local_hash", "local_bge"}


@dataclass(frozen=True)
class RuntimeConfigFieldSpec:
    key: str
    label: str
    section: str
    value_type: str
    secret: bool = False
    options: tuple[str, ...] = ()


CONFIG_FIELD_SPECS: tuple[RuntimeConfigFieldSpec, ...] = (
    RuntimeConfigFieldSpec("source_storage_dir", "Source storage directory", "storage", "path"),
    RuntimeConfigFieldSpec(
        "indexing_artifact_storage_dir",
        "Indexing artifact directory",
        "storage",
        "path",
    ),
    RuntimeConfigFieldSpec("max_upload_bytes", "Max upload bytes", "storage", "integer"),
    RuntimeConfigFieldSpec(
        "default_file_parser",
        "Default file parser",
        "parser",
        "select",
        options=("simple_directory_reader", "llamaparse"),
    ),
    RuntimeConfigFieldSpec(
        "llamaparse_default_tier",
        "LlamaParse tier",
        "parser",
        "select",
        options=("fast", "cost_effective", "agentic", "agentic_plus"),
    ),
    RuntimeConfigFieldSpec("llamaparse_default_version", "LlamaParse version", "parser", "string"),
    RuntimeConfigFieldSpec(
        "llama_cloud_api_key",
        "LlamaCloud API key",
        "parser",
        "secret",
        secret=True,
    ),
    RuntimeConfigFieldSpec(
        "llamaparse_use_vendor_multimodal",
        "Use vendor multimodal",
        "parser",
        "boolean",
    ),
    RuntimeConfigFieldSpec(
        "llamaparse_vendor_multimodal_model",
        "Vendor multimodal model",
        "parser",
        "string",
    ),
    RuntimeConfigFieldSpec("llamaparse_take_screenshot", "Take screenshots", "parser", "boolean"),
    RuntimeConfigFieldSpec("vector_index_enabled", "Enable vector index", "vector", "boolean"),
    RuntimeConfigFieldSpec(
        "vector_sparse_index_enabled",
        "Enable sparse vector index",
        "vector",
        "boolean",
    ),
    RuntimeConfigFieldSpec("qdrant_url", "Qdrant URL", "vector", "string"),
    RuntimeConfigFieldSpec("qdrant_api_key", "Qdrant API key", "vector", "secret", secret=True),
    RuntimeConfigFieldSpec("retrieval_enabled", "Enable retrieval", "retrieval", "boolean"),
    RuntimeConfigFieldSpec("retrieval_default_top_k", "Default top K", "retrieval", "integer"),
    RuntimeConfigFieldSpec("retrieval_max_top_k", "Max top K", "retrieval", "integer"),
    RuntimeConfigFieldSpec(
        "retrieval_rerank_default_top_k",
        "Default rerank top K",
        "retrieval",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_answer_max_context_items",
        "Answer max context items",
        "retrieval",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_reranker",
        "Coarse reranker",
        "reranking",
        "select",
        options=("score_keyword",),
    ),
    RuntimeConfigFieldSpec(
        "retrieval_answer_generator",
        "Answer generator",
        "retrieval",
        "select",
        options=("extractive", "llm"),
    ),
    RuntimeConfigFieldSpec(
        "retrieval_query_transformation",
        "Query transformation",
        "query",
        "select",
        options=("original", "rewrite", "multi_query", "hyde"),
    ),
    RuntimeConfigFieldSpec(
        "retrieval_query_multi_query_count",
        "Multi-query count",
        "query",
        "integer",
    ),
    RuntimeConfigFieldSpec("retrieval_bm25_enabled", "Enable BM25", "hybrid", "boolean"),
    RuntimeConfigFieldSpec("retrieval_bm25_top_k", "BM25 top K", "hybrid", "integer"),
    RuntimeConfigFieldSpec(
        "retrieval_fusion_strategy",
        "Fusion strategy",
        "hybrid",
        "select",
        options=("rrf",),
    ),
    RuntimeConfigFieldSpec("retrieval_fusion_rrf_k", "RRF K", "hybrid", "integer"),
    RuntimeConfigFieldSpec(
        "retrieval_reranking_stages",
        "Reranking stages",
        "reranking",
        "string",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_reranker_fine_device",
        "Fine reranker device",
        "reranking",
        "select",
        options=("cpu", "cuda"),
    ),
    RuntimeConfigFieldSpec(
        "retrieval_reranker_fine_batch_size",
        "Fine reranker batch size",
        "reranking",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_reranker_fine_max_length",
        "Fine reranker max length",
        "reranking",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_reranker_coarse_top_k",
        "Coarse reranker top K",
        "reranking",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_reranker_fine_top_k",
        "Fine reranker top K",
        "reranking",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_context_strategy",
        "Context strategy",
        "context",
        "select",
        options=("child_with_parent", "node_only"),
    ),
    RuntimeConfigFieldSpec(
        "retrieval_context_max_length",
        "Context max length",
        "context",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_context_deduplication_threshold",
        "Context dedupe threshold",
        "context",
        "float",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_llm_temperature",
        "LLM temperature",
        "llm_runtime",
        "float",
    ),
    RuntimeConfigFieldSpec(
        "retrieval_llm_max_tokens",
        "LLM max tokens",
        "llm_runtime",
        "integer",
    ),
    RuntimeConfigFieldSpec(
        "openai_embedding_batch_size",
        "Embedding batch size",
        "llm_runtime",
        "integer",
    ),
)

CONFIG_FIELD_SPECS_BY_KEY = {spec.key: spec for spec in CONFIG_FIELD_SPECS}


async def resolve_effective_settings(session: AsyncSession, base_settings: Settings) -> Settings:
    data = base_settings.model_dump()
    config = await get_runtime_configuration(session)
    if config is not None:
        for spec in CONFIG_FIELD_SPECS:
            value = getattr(config, spec.key)
            if value is not None:
                data[spec.key] = _settings_value(spec, value)

    for binding, provider, model in await list_default_binding_details(session):
        if not provider.is_enabled or not model.is_enabled:
            continue
        _apply_model_binding(data, binding.binding_key, provider, model)

    return Settings(**data)


async def get_runtime_configuration(
    session: AsyncSession,
) -> AppRuntimeConfigurationModel | None:
    result = await session.execute(
        select(AppRuntimeConfigurationModel).where(
            AppRuntimeConfigurationModel.config_id == GLOBAL_CONFIG_ID
        )
    )
    return result.scalar_one_or_none()


async def ensure_runtime_configuration(session: AsyncSession) -> AppRuntimeConfigurationModel:
    config = await get_runtime_configuration(session)
    if config is not None:
        return config

    now = datetime.now(UTC)
    config = AppRuntimeConfigurationModel(
        config_id=GLOBAL_CONFIG_ID,
        created_at=now,
        updated_at=now,
    )
    session.add(config)
    await session.flush()
    return config


async def update_runtime_configuration(
    session: AsyncSession,
    *,
    values: dict[str, Any],
    updated_by: str,
) -> AppRuntimeConfigurationModel:
    config = await ensure_runtime_configuration(session)
    for key, value in values.items():
        spec = CONFIG_FIELD_SPECS_BY_KEY.get(key)
        if spec is None:
            raise InvalidRequestError(f"Unsupported configuration key: {key}")
        setattr(config, key, None if value is None else _coerce_config_value(spec, value))

    config.updated_by = updated_by
    config.updated_at = datetime.now(UTC)
    await session.flush()
    return config


def configuration_field_payload(
    *,
    base_settings: Settings,
    config: AppRuntimeConfigurationModel | None,
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for spec in CONFIG_FIELD_SPECS:
        db_value = getattr(config, spec.key) if config is not None else None
        source = "db" if db_value is not None else "env"
        raw_value = db_value if db_value is not None else getattr(base_settings, spec.key)
        fields.append(_configuration_field_payload(spec, raw_value, source))
    return fields


async def list_model_providers(session: AsyncSession) -> tuple[ModelProviderModel, ...]:
    result = await session.execute(select(ModelProviderModel).order_by(ModelProviderModel.name))
    return tuple(result.scalars().all())


async def get_model_provider(session: AsyncSession, provider_id: str) -> ModelProviderModel | None:
    result = await session.execute(
        select(ModelProviderModel).where(ModelProviderModel.provider_id == provider_id)
    )
    return result.scalar_one_or_none()


async def create_model_provider(
    session: AsyncSession,
    *,
    name: str,
    provider_type: str,
    base_url: str | None,
    api_key: str | None,
    is_enabled: bool,
) -> ModelProviderModel:
    if provider_type not in MODEL_PROVIDER_TYPES:
        raise InvalidRequestError(f"Unsupported provider type: {provider_type}")
    now = datetime.now(UTC)
    provider = ModelProviderModel(
        provider_id=f"provider_{uuid4().hex}",
        name=name.strip(),
        provider_type=provider_type,
        base_url=_clean_optional_string(base_url),
        api_key=_clean_optional_string(api_key),
        is_enabled=is_enabled,
        created_at=now,
        updated_at=now,
    )
    session.add(provider)
    await session.flush()
    return provider


async def update_model_provider(
    session: AsyncSession,
    provider_id: str,
    *,
    values: dict[str, Any],
) -> ModelProviderModel:
    provider = await get_model_provider(session, provider_id)
    if provider is None:
        raise NotFoundError(f"Model provider not found: {provider_id}")

    for key, value in values.items():
        if key == "provider_type" and value not in MODEL_PROVIDER_TYPES:
            raise InvalidRequestError(f"Unsupported provider type: {value}")
        if key in {"name", "provider_type", "base_url", "api_key", "is_enabled"}:
            setattr(provider, key, _clean_optional_string(value) if key != "is_enabled" else value)
    provider.updated_at = datetime.now(UTC)
    await session.flush()
    return provider


async def delete_model_provider(session: AsyncSession, provider_id: str) -> None:
    result = await session.execute(
        delete(ModelProviderModel).where(ModelProviderModel.provider_id == provider_id)
    )
    if not result.rowcount:
        raise NotFoundError(f"Model provider not found: {provider_id}")


async def list_provider_models(
    session: AsyncSession,
    provider_id: str | None = None,
) -> tuple[ProviderModelModel, ...]:
    stmt = select(ProviderModelModel).order_by(
        ProviderModelModel.ai_type,
        ProviderModelModel.model_name,
    )
    if provider_id is not None:
        stmt = stmt.where(ProviderModelModel.provider_id == provider_id)
    result = await session.execute(stmt)
    return tuple(result.scalars().all())


async def get_provider_model(session: AsyncSession, model_id: str) -> ProviderModelModel | None:
    result = await session.execute(
        select(ProviderModelModel).where(ProviderModelModel.model_id == model_id)
    )
    return result.scalar_one_or_none()


async def create_provider_model(
    session: AsyncSession,
    *,
    provider_id: str,
    model_name: str,
    display_name: str | None,
    ai_type: str,
    dimension: int | None,
    context_window: int | None,
    max_tokens: int | None,
    is_enabled: bool,
) -> ProviderModelModel:
    provider = await get_model_provider(session, provider_id)
    if provider is None:
        raise NotFoundError(f"Model provider not found: {provider_id}")
    _ensure_ai_type(ai_type)
    now = datetime.now(UTC)
    model = ProviderModelModel(
        model_id=f"model_{uuid4().hex}",
        provider_id=provider_id,
        model_name=model_name.strip(),
        display_name=_clean_optional_string(display_name),
        ai_type=ai_type,
        dimension=dimension,
        context_window=context_window,
        max_tokens=max_tokens,
        is_enabled=is_enabled,
        created_at=now,
        updated_at=now,
    )
    session.add(model)
    await session.flush()
    return model


async def update_provider_model(
    session: AsyncSession,
    model_id: str,
    *,
    values: dict[str, Any],
) -> ProviderModelModel:
    model = await get_provider_model(session, model_id)
    if model is None:
        raise NotFoundError(f"Provider model not found: {model_id}")

    for key, value in values.items():
        if key == "ai_type":
            _ensure_ai_type(str(value))
        if key in {
            "model_name",
            "display_name",
            "ai_type",
            "dimension",
            "context_window",
            "max_tokens",
            "is_enabled",
        }:
            setattr(model, key, _clean_optional_string(value) if key == "display_name" else value)
    model.updated_at = datetime.now(UTC)
    await session.flush()
    return model


async def delete_provider_model(session: AsyncSession, model_id: str) -> None:
    result = await session.execute(
        delete(ProviderModelModel).where(ProviderModelModel.model_id == model_id)
    )
    if not result.rowcount:
        raise NotFoundError(f"Provider model not found: {model_id}")


async def list_default_bindings(session: AsyncSession) -> tuple[ModelDefaultBindingModel, ...]:
    result = await session.execute(
        select(ModelDefaultBindingModel).order_by(ModelDefaultBindingModel.binding_key)
    )
    return tuple(result.scalars().all())


async def list_default_binding_details(
    session: AsyncSession,
) -> tuple[tuple[ModelDefaultBindingModel, ModelProviderModel, ProviderModelModel], ...]:
    stmt = (
        select(ModelDefaultBindingModel, ModelProviderModel, ProviderModelModel)
        .join(ProviderModelModel, ProviderModelModel.model_id == ModelDefaultBindingModel.model_id)
        .join(ModelProviderModel, ModelProviderModel.provider_id == ProviderModelModel.provider_id)
        .order_by(ModelDefaultBindingModel.binding_key)
    )
    result = await session.execute(stmt)
    return tuple((binding, provider, model) for binding, provider, model in result.all())


async def update_default_bindings(
    session: AsyncSession,
    *,
    bindings: dict[str, str | None],
    updated_by: str,
) -> tuple[ModelDefaultBindingModel, ...]:
    now = datetime.now(UTC)
    for binding_key, model_id in bindings.items():
        if binding_key not in MODEL_BINDING_KEYS:
            raise InvalidRequestError(f"Unsupported binding key: {binding_key}")
        if model_id is None:
            await session.execute(
                delete(ModelDefaultBindingModel).where(
                    ModelDefaultBindingModel.binding_key == binding_key
                )
            )
            continue

        model = await get_provider_model(session, model_id)
        if model is None:
            raise NotFoundError(f"Provider model not found: {model_id}")
        _ensure_binding_matches_model(binding_key, model)

        existing_result = await session.execute(
            select(ModelDefaultBindingModel).where(
                ModelDefaultBindingModel.binding_key == binding_key
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is None:
            session.add(
                ModelDefaultBindingModel(
                    binding_key=binding_key,
                    model_id=model_id,
                    updated_by=updated_by,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            existing.model_id = model_id
            existing.updated_by = updated_by
            existing.updated_at = now

    await session.flush()
    return await list_default_bindings(session)


def provider_presets() -> list[dict[str, Any]]:
    return [
        {
            "name": "OpenAI",
            "provider_type": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "capabilities": ["llm", "embedding"],
        },
        {
            "name": "DeepSeek",
            "provider_type": "openai_compatible",
            "base_url": "https://api.deepseek.com/v1",
            "capabilities": ["llm"],
        },
        {
            "name": "Moonshot",
            "provider_type": "openai_compatible",
            "base_url": "https://api.moonshot.cn/v1",
            "capabilities": ["llm"],
        },
        {
            "name": "Tongyi-Qianwen",
            "provider_type": "openai_compatible",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "capabilities": ["llm", "embedding"],
        },
        {
            "name": "ZHIPU-AI",
            "provider_type": "openai_compatible",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "capabilities": ["llm", "embedding"],
        },
        {
            "name": "Local Hash",
            "provider_type": "local_hash",
            "base_url": None,
            "capabilities": ["embedding"],
        },
        {
            "name": "Local BGE",
            "provider_type": "local_bge",
            "base_url": None,
            "capabilities": ["rerank"],
        },
    ]


def _configuration_field_payload(
    spec: RuntimeConfigFieldSpec,
    value: Any,
    source: str,
) -> dict[str, Any]:
    if isinstance(value, SecretStr):
        secret_value = value.get_secret_value()
    else:
        secret_value = str(value) if value is not None else ""

    if spec.secret:
        return {
            "key": spec.key,
            "label": spec.label,
            "section": spec.section,
            "value_type": spec.value_type,
            "secret": True,
            "options": list(spec.options),
            "source": source,
            "value": None,
            "is_configured": bool(secret_value),
            "masked_value": _mask_secret(secret_value),
        }

    serializable_value = str(value) if isinstance(value, Path) else value
    return {
        "key": spec.key,
        "label": spec.label,
        "section": spec.section,
        "value_type": spec.value_type,
        "secret": False,
        "options": list(spec.options),
        "source": source,
        "value": serializable_value,
        "is_configured": serializable_value is not None,
        "masked_value": None,
    }


def _settings_value(spec: RuntimeConfigFieldSpec, value: Any) -> Any:
    if spec.secret:
        return SecretStr(str(value)) if value else None
    if spec.value_type == "path":
        return Path(str(value))
    return value


def _coerce_config_value(spec: RuntimeConfigFieldSpec, value: Any) -> Any:
    if spec.value_type in {"string", "select", "path", "secret"}:
        cleaned = _clean_optional_string(value)
        if cleaned is None:
            raise InvalidRequestError(f"Configuration '{spec.key}' must not be empty.")
        if spec.options and cleaned not in spec.options:
            raise InvalidRequestError(
                f"Configuration '{spec.key}' must be one of: {', '.join(spec.options)}."
            )
        return cleaned
    if spec.value_type == "integer":
        return int(value)
    if spec.value_type == "float":
        return float(value)
    if spec.value_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
        raise InvalidRequestError(f"Configuration '{spec.key}' must be boolean.")
    raise InvalidRequestError(f"Unsupported configuration type: {spec.value_type}")


def _apply_model_binding(
    data: dict[str, Any],
    binding_key: str,
    provider: ModelProviderModel,
    model: ProviderModelModel,
) -> None:
    if binding_key == "embedding" and model.ai_type == "embedding":
        if provider.provider_type == "local_hash":
            data["embedding_provider"] = "hash"
            data["hash_embedding_model"] = model.model_name
        elif provider.provider_type == "openai_compatible":
            data["embedding_provider"] = "openai"
            data["openai_embedding_model"] = model.model_name
            data["openai_base_url"] = provider.base_url
            if provider.api_key:
                data["openai_api_key"] = SecretStr(provider.api_key)
        if model.dimension is not None:
            data["embedding_dimension"] = model.dimension

    if binding_key == "answer_llm" and model.ai_type == "llm":
        if provider.provider_type == "openai_compatible":
            data["retrieval_answer_generator"] = "llm"
            data["retrieval_llm_provider"] = "openai"
            data["retrieval_llm_model"] = model.model_name
            data["retrieval_llm_base_url"] = provider.base_url
            if provider.api_key:
                data["retrieval_llm_api_key"] = SecretStr(provider.api_key)
            if model.max_tokens is not None:
                data["retrieval_llm_max_tokens"] = model.max_tokens

    if binding_key == "query_llm" and model.ai_type == "llm":
        if provider.provider_type == "openai_compatible":
            data["retrieval_query_llm_provider"] = "openai"
            data["retrieval_query_llm_model"] = model.model_name
            data["retrieval_query_llm_base_url"] = provider.base_url
            if provider.api_key:
                data["retrieval_query_llm_api_key"] = SecretStr(provider.api_key)

    if binding_key == "rerank" and model.ai_type == "rerank":
        if provider.provider_type == "local_bge":
            data["retrieval_reranking_stages"] = "coarse,fine"
            data["retrieval_reranker_fine"] = "bge"
            data["retrieval_reranker_fine_model"] = model.model_name


def _ensure_ai_type(ai_type: str) -> None:
    if ai_type not in MODEL_AI_TYPES:
        raise InvalidRequestError(f"Unsupported model AI type: {ai_type}")


def _ensure_binding_matches_model(binding_key: str, model: ProviderModelModel) -> None:
    expected = {
        "answer_llm": "llm",
        "query_llm": "llm",
        "embedding": "embedding",
        "rerank": "rerank",
    }[binding_key]
    if model.ai_type != expected:
        raise InvalidRequestError(
            f"Binding '{binding_key}' requires a model with ai_type='{expected}'."
        )


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _mask_secret(value: str) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"
