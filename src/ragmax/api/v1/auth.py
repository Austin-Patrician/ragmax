from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ragmax.api.auth_dependencies import AuthenticatedUser, get_current_user
from ragmax.core.config import Settings, get_settings
from ragmax.core.security import (
    access_token_expires_in_seconds,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expires_at,
    refresh_token_max_age_seconds,
    verify_password,
)
from ragmax.infrastructure.db.repositories.auth import (
    create_refresh_session,
    get_active_refresh_session,
    get_user_by_id,
    get_user_by_username,
    list_user_route_permissions,
)
from ragmax.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


class AuthUserResponse(BaseModel):
    user_id: str
    username: str
    route_permissions: list[str]


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse


@router.post("/login", response_model=AuthTokenResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthTokenResponse:
    user = await get_user_by_username(session, request.username)
    if (
        user is None
        or not user.is_active
        or not verify_password(request.password, user.password_hash)
    ):
        raise _invalid_credentials()

    route_permissions = await list_user_route_permissions(session, user.user_id)
    token_response, refresh_token = _build_token_pair(
        user_id=user.user_id,
        username=user.username,
        route_permissions=route_permissions,
        settings=settings,
    )
    session.add(
        create_refresh_session(
            user_id=user.user_id,
            token_hash=hash_refresh_token(refresh_token, settings),
            expires_at=refresh_token_expires_at(settings),
        )
    )
    await session.commit()
    _set_refresh_cookie(response, refresh_token, settings)
    return token_response


@router.post("/refresh", response_model=AuthTokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthTokenResponse:
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if not refresh_token:
        raise _invalid_refresh_token()

    now = datetime.now(UTC)
    refresh_session = await get_active_refresh_session(
        session,
        token_hash=hash_refresh_token(refresh_token, settings),
        now=now,
    )
    if refresh_session is None:
        _delete_refresh_cookie(response, settings)
        raise _invalid_refresh_token()

    user = await get_user_by_id(session, refresh_session.user_id)
    if user is None or not user.is_active:
        refresh_session.revoked_at = now
        refresh_session.last_used_at = now
        await session.commit()
        _delete_refresh_cookie(response, settings)
        raise _invalid_refresh_token()

    route_permissions = await list_user_route_permissions(session, user.user_id)
    token_response, rotated_refresh_token = _build_token_pair(
        user_id=user.user_id,
        username=user.username,
        route_permissions=route_permissions,
        settings=settings,
    )
    refresh_session.revoked_at = now
    refresh_session.last_used_at = now
    session.add(
        create_refresh_session(
            user_id=user.user_id,
            token_hash=hash_refresh_token(rotated_refresh_token, settings),
            expires_at=refresh_token_expires_at(settings),
        )
    )
    await session.commit()
    _set_refresh_cookie(response, rotated_refresh_token, settings)
    return token_response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if refresh_token:
        now = datetime.now(UTC)
        refresh_session = await get_active_refresh_session(
            session,
            token_hash=hash_refresh_token(refresh_token, settings),
            now=now,
        )
        if refresh_session is not None:
            refresh_session.revoked_at = now
            refresh_session.last_used_at = now
            await session.commit()
    _delete_refresh_cookie(response, settings)


@router.get("/me", response_model=AuthUserResponse)
async def me(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthUserResponse:
    return _user_response(
        user_id=current_user.user_id,
        username=current_user.username,
        route_permissions=current_user.route_permissions,
    )


def _build_token_pair(
    *,
    user_id: str,
    username: str,
    route_permissions: tuple[str, ...],
    settings: Settings,
) -> tuple[AuthTokenResponse, str]:
    access_token = create_access_token(
        user_id=user_id,
        username=username,
        route_permissions=route_permissions,
        settings=settings,
    )
    return (
        AuthTokenResponse(
            access_token=access_token,
            expires_in=access_token_expires_in_seconds(settings),
            user=_user_response(
                user_id=user_id,
                username=username,
                route_permissions=route_permissions,
            ),
        ),
        generate_refresh_token(),
    )


def _user_response(
    *,
    user_id: str,
    username: str,
    route_permissions: tuple[str, ...],
) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=user_id,
        username=username,
        route_permissions=list(route_permissions),
    )


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=token,
        max_age=refresh_token_max_age_seconds(settings),
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=f"{settings.api_v1_prefix}/auth",
    )


def _delete_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=f"{settings.api_v1_prefix}/auth",
    )


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _invalid_refresh_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token is invalid or expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
