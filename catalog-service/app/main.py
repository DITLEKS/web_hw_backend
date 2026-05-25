from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from app.database import create_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await create_pool()
    yield
    await app.state.pool.close()

tags_metadata = [
    {"name": "Категории", "description": "Справочник категорий товаров."},
    {"name": "Товары", "description": "Управление каталогом товаров."},
    {"name": "Служебные", "description": "Health check и проверка доступности сервиса."},
]

app = FastAPI(
    title="SmartLight — Сервис управления товарами",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={"error": "server_error", "message": str(detail)})


from app.routers import categories, products

app.include_router(categories.router, prefix="/api/v1/categories", tags=["Категории"])
app.include_router(products.router,   prefix="/api/v1/products",   tags=["Товары"])

@app.get("/health", tags=["Служебные"])
async def health():
    return {"status": "ok", "service": "catalog-service"}
