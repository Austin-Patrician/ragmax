from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ragmax.core.config import Settings, get_settings
from ragmax.core.security import TokenError, decode_access_token
from ragmax.infrastructure.db.repositories.auth import (
    get_user_by_id,
    list_user_route_permissions,
)
from ragmax.infrastructure.db.session import get_db_session

ROUTE_INDEXING = "/indexing"
ROUTE_RETRIEVAL = "/retrieval"
ROUTE_EVALUATION = "/evaluation"

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    username: str
    route_permissions: tuple[str, ...]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials, settings)
    except TokenError as exc:
        raise _unauthorized(str(exc)) from exc

    user_id = str(payload["sub"])
    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("User is inactive or no longer exists.")

    route_permissions = await list_user_route_permissions(session, user.user_id)
    return AuthenticatedUser(
        user_id=user.user_id,
        username=user.username,
        route_permissions=route_permissions,
    )


def require_route_permission(route_path: str):
    async def dependency(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if route_path not in current_user.route_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this route.",
            )
        return current_user

    return dependency


def _unauthorized(detail: str = "Not authenticated.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
