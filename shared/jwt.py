from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError


def create_access_token(
    subject: str,
    email: str,
    role: str,
    secret_key: str,
    algorithm: str,
    expires_in: int,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def create_refresh_token(
    subject: str,
    email: str,
    role: str,
    secret_key: str,
    algorithm: str,
    expires_in: int,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_token(token: str, secret_key: str, algorithms: list[str]) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret_key, algorithms=algorithms)
    except ExpiredSignatureError as exc:
        raise
    except InvalidTokenError as exc:
        raise
