from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ragmax.core.security import hash_password
from ragmax.infrastructure.db.models import (
    AuthRefreshSessionModel,
    UserModel,
    UserRoutePermissionModel,
    utc_now,
)

_ROUTE_PERMISSION_ORDER = {
    "/files": 0,
    "/datasets": 1,
    "/indexing": 2,
    "/retrieval": 3,
    "/evaluation": 4,
}


async def get_user_by_id(session: AsyncSession, user_id: str) -> UserModel | None:
    result = await session.execute(select(UserModel).where(UserModel.user_id == user_id))
    return result.scalars().one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> UserModel | None:
    result = await session.execute(select(UserModel).where(UserModel.username == username))
    return result.scalars().one_or_none()


async def list_user_route_permissions(session: AsyncSession, user_id: str) -> tuple[str, ...]:
    result = await session.execute(
        select(UserRoutePermissionModel.route_path)
        .where(UserRoutePermissionModel.user_id == user_id)
        .order_by(UserRoutePermissionModel.route_path)
    )
    routes = result.scalars().all()
    return tuple(
        sorted(
            routes,
            key=_route_permission_sort_key,
        )
    )


def _route_permission_sort_key(route: str) -> tuple[int, str]:
    return (_ROUTE_PERMISSION_ORDER.get(route, len(_ROUTE_PERMISSION_ORDER)), route)


async def get_active_refresh_session(
    session: AsyncSession,
    *,
    token_hash: str,
    now: datetime,
) -> AuthRefreshSessionModel | None:
    result = await session.execute(
        select(AuthRefreshSessionModel).where(
            AuthRefreshSessionModel.token_hash == token_hash,
            AuthRefreshSessionModel.revoked_at.is_(None),
            AuthRefreshSessionModel.expires_at > now,
        )
    )
    return result.scalars().one_or_none()


def create_refresh_session(
    *,
    user_id: str,
    token_hash: str,
    expires_at: datetime,
) -> AuthRefreshSessionModel:
    return AuthRefreshSessionModel(
        session_id=f"rfs_{uuid4().hex}",
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=utc_now(),
        last_used_at=utc_now(),
    )


async def bootstrap_auth_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    username: str,
    password: str,
    routes: list[str],
) -> None:
    normalized_routes = sorted({route for route in routes if route.startswith("/")})
    if not normalized_routes:
        raise ValueError("At least one bootstrap route permission is required.")

    async with session_factory() as session:
        user = await get_user_by_username(session, username)
        if user is None:
            user = UserModel(
                user_id=f"user_{uuid4().hex}",
                username=username,
                password_hash=hash_password(password),
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(user)
            await session.flush()
        else:
            user.password_hash = hash_password(password)
            user.is_active = True
            user.updated_at = utc_now()

        await session.execute(
            delete(UserRoutePermissionModel).where(
                UserRoutePermissionModel.user_id == user.user_id
            )
        )
        session.add_all(
            UserRoutePermissionModel(
                permission_id=f"urp_{uuid4().hex}",
                user_id=user.user_id,
                route_path=route,
                created_at=utc_now(),
            )
            for route in normalized_routes
        )
        await session.commit()
