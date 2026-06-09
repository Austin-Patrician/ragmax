from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ragmax.api.auth_dependencies import AuthenticatedUser, get_current_user
from ragmax.core.config import Settings, get_settings
from ragmax.core.exceptions import InvalidRequestError, NotFoundError
from ragmax.infrastructure.db.repositories import user_settings as repo
from ragmax.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


class UserSettingsProfileResponse(BaseModel):
    user_id: str
    username: str
    route_permissions: list[str]


class RuntimeConfigurationFieldResponse(BaseModel):
    key: str
    label: str
    section: str
    value_type: str
    secret: bool
    options: list[str]
    source: str
    value: Any
    is_configured: bool
    masked_value: str | None


class RuntimeConfigurationResponse(BaseModel):
    fields: list[RuntimeConfigurationFieldResponse]


class UpdateRuntimeConfigurationRequest(BaseModel):
    values: dict[str, Any | None] = Field(default_factory=dict)


class ProviderModelResponse(BaseModel):
    model_id: str
    provider_id: str
    model_name: str
    display_name: str | None
    ai_type: str
    dimension: int | None
    context_window: int | None
    max_tokens: int | None
    is_enabled: bool
    created_at: str | None
    updated_at: str | None


class ModelProviderResponse(BaseModel):
    provider_id: str
    name: str
    provider_type: str
    base_url: str | None
    api_key_configured: bool
    api_key_masked: str | None
    is_enabled: bool
    models: list[ProviderModelResponse]
    created_at: str | None
    updated_at: str | None


class ProviderPresetResponse(BaseModel):
    name: str
    provider_type: str
    base_url: str | None
    capabilities: list[str]


class ModelDefaultBindingResponse(BaseModel):
    binding_key: str
    model_id: str
    updated_by: str | None
    created_at: str | None
    updated_at: str | None


class ModelProviderSettingsResponse(BaseModel):
    providers: list[ModelProviderResponse]
    defaults: list[ModelDefaultBindingResponse]
    presets: list[ProviderPresetResponse]
    ai_types: list[str]
    binding_keys: list[str]
    provider_types: list[str]


class CreateModelProviderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    provider_type: str
    base_url: str | None = None
    api_key: str | None = None
    is_enabled: bool = True


class UpdateModelProviderRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    is_enabled: bool | None = None


class CreateProviderModelRequest(BaseModel):
    model_name: str = Field(min_length=1, max_length=255)
    display_name: str | None = None
    ai_type: str
    dimension: int | None = Field(default=None, ge=1)
    context_window: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    is_enabled: bool = True


class UpdateProviderModelRequest(BaseModel):
    model_name: str | None = Field(default=None, min_length=1, max_length=255)
    display_name: str | None = None
    ai_type: str | None = None
    dimension: int | None = Field(default=None, ge=1)
    context_window: int | None = Field(default=None, ge=1)
    max_tokens: int | None = Field(default=None, ge=1)
    is_enabled: bool | None = None


class UpdateDefaultBindingsRequest(BaseModel):
    bindings: dict[str, str | None] = Field(default_factory=dict)


@router.get("/profile", response_model=UserSettingsProfileResponse)
async def get_profile(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserSettingsProfileResponse:
    return UserSettingsProfileResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        route_permissions=list(current_user.route_permissions),
    )


@router.get("/configuration", response_model=RuntimeConfigurationResponse)
async def get_configuration(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RuntimeConfigurationResponse:
    del current_user
    config = await repo.get_runtime_configuration(session)
    return RuntimeConfigurationResponse(
        fields=repo.configuration_field_payload(base_settings=settings, config=config)
    )


@router.patch("/configuration", response_model=RuntimeConfigurationResponse)
async def update_configuration(
    request: UpdateRuntimeConfigurationRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RuntimeConfigurationResponse:
    try:
        config = await repo.update_runtime_configuration(
            session,
            values=request.values,
            updated_by=current_user.user_id,
        )
        await session.commit()
        return RuntimeConfigurationResponse(
            fields=repo.configuration_field_payload(base_settings=settings, config=config)
        )
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


@router.get("/model-providers", response_model=ModelProviderSettingsResponse)
async def get_model_provider_settings(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ModelProviderSettingsResponse:
    del current_user
    return await _model_provider_settings_response(session)


@router.post(
    "/model-providers",
    response_model=ModelProviderSettingsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model_provider(
    request: CreateModelProviderRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ModelProviderSettingsResponse:
    del current_user
    try:
        await repo.create_model_provider(
            session,
            name=request.name,
            provider_type=request.provider_type,
            base_url=request.base_url,
            api_key=request.api_key,
            is_enabled=request.is_enabled,
        )
        await session.commit()
        return await _model_provider_settings_response(session)
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


@router.patch("/model-providers/defaults", response_model=ModelProviderSettingsResponse)
async def update_model_defaults(
    request: UpdateDefaultBindingsRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ModelProviderSettingsResponse:
    try:
        await repo.update_default_bindings(
            session,
            bindings=request.bindings,
            updated_by=current_user.user_id,
        )
        await session.commit()
        return await _model_provider_settings_response(session)
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


@router.patch("/model-providers/{provider_id}", response_model=ModelProviderSettingsResponse)
async def update_model_provider(
    provider_id: str,
    request: UpdateModelProviderRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ModelProviderSettingsResponse:
    del current_user
    try:
        await repo.update_model_provider(
            session,
            provider_id,
            values=request.model_dump(exclude_unset=True),
        )
        await session.commit()
        return await _model_provider_settings_response(session)
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


@router.delete("/model-providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_provider(
    provider_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    del current_user
    try:
        await repo.delete_model_provider(session, provider_id)
        await session.commit()
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


@router.post(
    "/model-providers/{provider_id}/models",
    response_model=ModelProviderSettingsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_provider_model(
    provider_id: str,
    request: CreateProviderModelRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ModelProviderSettingsResponse:
    del current_user
    try:
        await repo.create_provider_model(
            session,
            provider_id=provider_id,
            model_name=request.model_name,
            display_name=request.display_name,
            ai_type=request.ai_type,
            dimension=request.dimension,
            context_window=request.context_window,
            max_tokens=request.max_tokens,
            is_enabled=request.is_enabled,
        )
        await session.commit()
        return await _model_provider_settings_response(session)
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


@router.patch(
    "/model-providers/{provider_id}/models/{model_id}",
    response_model=ModelProviderSettingsResponse,
)
async def update_provider_model(
    provider_id: str,
    model_id: str,
    request: UpdateProviderModelRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ModelProviderSettingsResponse:
    del current_user
    del provider_id
    try:
        await repo.update_provider_model(
            session,
            model_id,
            values=request.model_dump(exclude_unset=True),
        )
        await session.commit()
        return await _model_provider_settings_response(session)
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


@router.delete(
    "/model-providers/{provider_id}/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_provider_model(
    provider_id: str,
    model_id: str,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    del current_user
    del provider_id
    try:
        await repo.delete_provider_model(session, model_id)
        await session.commit()
    except (InvalidRequestError, NotFoundError) as exc:
        await session.rollback()
        raise _http_error(exc) from exc


async def _model_provider_settings_response(
    session: AsyncSession,
) -> ModelProviderSettingsResponse:
    providers = await repo.list_model_providers(session)
    models = await repo.list_provider_models(session)
    models_by_provider: dict[str, list[ProviderModelResponse]] = {}
    for model in models:
        models_by_provider.setdefault(model.provider_id, []).append(_model_response(model))

    return ModelProviderSettingsResponse(
        providers=[
            _provider_response(provider, models_by_provider.get(provider.provider_id, []))
            for provider in providers
        ],
        defaults=[
            ModelDefaultBindingResponse(
                binding_key=binding.binding_key,
                model_id=binding.model_id,
                updated_by=binding.updated_by,
                created_at=_isoformat(binding.created_at),
                updated_at=_isoformat(binding.updated_at),
            )
            for binding in await repo.list_default_bindings(session)
        ],
        presets=[ProviderPresetResponse(**preset) for preset in repo.provider_presets()],
        ai_types=sorted(repo.MODEL_AI_TYPES),
        binding_keys=sorted(repo.MODEL_BINDING_KEYS),
        provider_types=sorted(repo.MODEL_PROVIDER_TYPES),
    )


def _provider_response(
    provider,
    models: list[ProviderModelResponse],
) -> ModelProviderResponse:
    return ModelProviderResponse(
        provider_id=provider.provider_id,
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        api_key_configured=bool(provider.api_key),
        api_key_masked=_mask_secret(provider.api_key),
        is_enabled=provider.is_enabled,
        models=models,
        created_at=_isoformat(provider.created_at),
        updated_at=_isoformat(provider.updated_at),
    )


def _model_response(model) -> ProviderModelResponse:
    return ProviderModelResponse(
        model_id=model.model_id,
        provider_id=model.provider_id,
        model_name=model.model_name,
        display_name=model.display_name,
        ai_type=model.ai_type,
        dimension=model.dimension,
        context_window=model.context_window,
        max_tokens=model.max_tokens,
        is_enabled=model.is_enabled,
        created_at=_isoformat(model.created_at),
        updated_at=_isoformat(model.updated_at),
    )


def _mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _isoformat(value) -> str | None:
    return value.isoformat() if value is not None else None


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
