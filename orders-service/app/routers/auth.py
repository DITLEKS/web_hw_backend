from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
import asyncpg

from app.core.config import settings
from app.database import get_pool
from app.schemas import (
    AuthLoginResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    UserOut,
)
from shared.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from shared.security import verify_password

router = APIRouter()


async def get_admin_record(pool: asyncpg.Pool, email: str) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT id, email, first_name, last_name, role, password_hash, is_active FROM admins WHERE email = $1",
        email,
    )


@router.post("/login", response_model=AuthLoginResponse)
async def login(body: LoginRequest, pool: asyncpg.Pool = Depends(get_pool)):
    admin = await get_admin_record(pool, body.email)
    if not admin or not verify_password(body.password, admin["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_credentials", "message": "Неверный логин или пароль"},
        )

    if not admin["is_active"]:
        raise HTTPException(
            status_code=403,
            detail={"error": "account_locked", "message": "Аккаунт заблокирован"},
        )

    access_token = create_access_token(
        subject=admin["id"],
        email=admin["email"],
        role=admin["role"],
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_in=settings.access_token_expire_seconds,
    )
    refresh_token = create_refresh_token(
        subject=admin["id"],
        email=admin["email"],
        role=admin["role"],
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_in=settings.refresh_token_expire_seconds,
    )

    return {
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": settings.access_token_expire_seconds,
            "user": UserOut(
                id=admin["id"],
                email=admin["email"],
                first_name=admin["first_name"],
                last_name=admin["last_name"],
                role=admin["role"],
            ).model_dump(),
        }
    }


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(
            body.refresh_token,
            settings.jwt_secret_key,
            [settings.jwt_algorithm],
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_credentials", "message": "Неверный refresh token"},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_credentials", "message": "Неверный refresh token"},
        )

    access_token = create_access_token(
        subject=payload["sub"],
        email=payload["email"],
        role=payload["role"],
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_in=settings.access_token_expire_seconds,
    )

    return {"data": {"access_token": access_token, "expires_in": settings.access_token_expire_seconds}}


@router.post("/logout", status_code=204, responses={204: {"description": "Logout successful"}})
async def logout() -> Response:
    return Response(status_code=204)
