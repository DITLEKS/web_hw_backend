from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.jwt import decode_token
from jwt import ExpiredSignatureError, InvalidTokenError

security = HTTPBearer(auto_error=False)


def create_admin_dependency(secret_key: str, algorithm: str):
    async def get_current_admin(
        authorization: HTTPAuthorizationCredentials = Depends(security),
    ) -> dict[str, Any]:
        if not authorization or authorization.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Требуется JWT"},
            )

        try:
            payload = decode_token(authorization.credentials, secret_key, [algorithm])
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "JWT истек"},
            )
        except InvalidTokenError:
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Требуется JWT"},
            )

        if payload.get("type") != "access" or payload.get("role") != "admin":
            raise HTTPException(
                status_code=401,
                detail={"error": "unauthorized", "message": "Требуется JWT"},
            )

        return payload

    return get_current_admin
