from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .config import APP_VERSION, ALLOWED_ORIGINS
from .db import fetch_all
from .schemas import OrderCreate
from .services import list_products, get_product, create_order

app = FastAPI(title="PartsHub API", version=APP_VERSION, docs_url="/docs", redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])

@app.get("/api/v1/health")
def health():
    return {"status":"ok","version":APP_VERSION}

@app.get("/api/v1/meta")
def meta():
    settings={row['key']:row['value'] for row in fetch_all("SELECT key,value FROM settings")}
    return {"version":APP_VERSION,"currency":"TWD","locale":"zh-TW","settings":settings}

@app.get("/api/v1/products")
def products(q: str = Query(default="", max_length=120)):
    items = list_products(q)
    return {"items": items, "count": len(items)}

@app.get("/api/v1/products/{product_id}")
def product(product_id: int):
    item=get_product(product_id)
    if not item: raise HTTPException(status_code=404,detail="找不到商品")
    return item

@app.post("/api/v1/orders", status_code=201)
def order(payload: OrderCreate):
    try:
        return create_order([item.model_dump() for item in payload.items])
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@app.get("/api/v1/admin/products")
def admin_products():
    items = list_products()
    return {"items": items, "count": len(items)}

@app.get("/api/v1/admin/source-pages")
def source_pages():
    return {"items":fetch_all("SELECT * FROM source_pages ORDER BY id")}

@app.get("/api/v1/admin/orders")
def orders():
    return {"items":fetch_all("SELECT * FROM orders ORDER BY id DESC LIMIT 100")}
