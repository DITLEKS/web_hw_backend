import os, httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Admin Service")
security = HTTPBearer()

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "admin@test.ru")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
JWT_SECRET     = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM  = "HS256"
CATALOG_URL    = os.getenv("CATALOG_URL", "http://localhost:3001")
ORDERS_URL     = os.getenv("ORDERS_URL",  "http://localhost:3002")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

def create_token(email: str) -> str:
    payload = {
        "sub": email,
        "type": "access",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/v1/auth/login")
async def login(data: LoginRequest):
    if data.email != ADMIN_EMAIL or data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(data.email)
    return {
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "email": data.email,
                "name": "Admin",
                "role": "admin"
            }
        }
    }

@app.post("/api/v1/auth/refresh")
async def refresh(email: str = Depends(verify_token)):
    return {"access_token": create_token(email), "token_type": "bearer"}

@app.get("/api/v1/dashboard")
async def dashboard(email: str = Depends(verify_token)):
    token = create_token(email)
    async with httpx.AsyncClient() as client:
        orders_r  = await client.get(
            f"{ORDERS_URL}/api/v1/orders?page=1&limit=100",
            headers={"Authorization": f"Bearer {token}"}
        )
        catalog_r = await client.get(f"{CATALOG_URL}/api/v1/products?limit=100")

    orders_json  = orders_r.json()  if orders_r.status_code == 200 else {}
    catalog_json = catalog_r.json() if catalog_r.status_code == 200 else {}

    orders_list = (
        orders_json.get("items") or
        orders_json.get("data") or
        (orders_json if isinstance(orders_json, list) else [])
    )
    products_list = (
        catalog_json.get("items") or
        catalog_json.get("data") or
        (catalog_json if isinstance(catalog_json, list) else [])
    )

    low_stock = [
        p for p in products_list
        if int(p.get("stock_quantity") or 0) < 10
    ]

    new_customers = len({
        (o.get("customer") or {}).get("email", "") or o.get("customer_email", "")
        for o in orders_list
    } - {""})

    total_revenue = sum(
        float(o.get("total_amount") or o.get("total_price") or 0)
        for o in orders_list
    )
    recent = sorted(
        orders_list,
        key=lambda o: o.get("created_at", ""),
        reverse=True
    )[:5]

    return {
        "orders_count":   orders_json.get("total") or len(orders_list),
        "revenue":        total_revenue,
        "products_count": len(products_list),
        "low_stock":      low_stock,
        "new_customers":  new_customers,
        "recent_orders":  recent,
    }