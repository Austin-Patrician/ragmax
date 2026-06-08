from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from ragmax.core.config import Settings

JWT_ALGORITHM = "HS256"
PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 310_000


class TokenError(ValueError):
    """Raised when a bearer token is malformed, expired, or unverifiable."""


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        (
            PASSWORD_ALGORITHM,
            str(PASSWORD_ITERATIONS),
            _b64_encode(salt),
            _b64_encode(digest),
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_value, salt_value, digest_value = password_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        iterations = int(iterations_value)
        salt = _b64_decode(salt_value)
        expected_digest = _b64_decode(digest_value)
    except (TypeError, ValueError):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_access_token(
    *,
    user_id: str,
    username: str,
    route_permissions: tuple[str, ...],
    settings: Settings,
) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.auth_access_token_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "route_permissions": list(route_permissions),
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return _encode_jwt(payload, settings)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    payload = _decode_jwt(token, settings)
    if payload.get("token_type") != "access":
        raise TokenError("Invalid token type.")
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(datetime.now(UTC).timestamp()):
        raise TokenError("Token has expired.")
    if not isinstance(payload.get("sub"), str):
        raise TokenError("Token subject is missing.")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str, settings: Settings) -> str:
    return hmac.new(
        _jwt_secret(settings).encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def access_token_expires_in_seconds(settings: Settings) -> int:
    return settings.auth_access_token_minutes * 60


def refresh_token_expires_at(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.auth_refresh_token_days)


def refresh_token_max_age_seconds(settings: Settings) -> int:
    return settings.auth_refresh_token_days * 24 * 60 * 60


def _encode_jwt(payload: dict[str, Any], settings: Settings) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    signing_input = ".".join((_json_b64_encode(header), _json_b64_encode(payload)))
    signature = hmac.new(
        _jwt_secret(settings).encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64_encode(signature)}"


def _decode_jwt(token: str, settings: Settings) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("Malformed token.")
    header_value, payload_value, signature_value = parts
    signing_input = f"{header_value}.{payload_value}"
    expected_signature = hmac.new(
        _jwt_secret(settings).encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        actual_signature = _b64_decode(signature_value)
    except ValueError as exc:
        raise TokenError("Malformed signature.") from exc
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise TokenError("Invalid signature.")

    try:
        header = json.loads(_b64_decode(header_value))
        payload = json.loads(_b64_decode(payload_value))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise TokenError("Malformed token payload.") from exc
    if header.get("alg") != JWT_ALGORITHM or header.get("typ") != "JWT":
        raise TokenError("Unsupported token header.")
    if not isinstance(payload, dict):
        raise TokenError("Malformed token payload.")
    return payload


def _json_b64_encode(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64_encode(encoded)


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Invalid base64 value.") from exc


def _jwt_secret(settings: Settings) -> str:
    return settings.auth_jwt_secret.get_secret_value()
