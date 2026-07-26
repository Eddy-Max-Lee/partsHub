from __future__ import annotations
import hashlib
import json
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import APP_VERSION, ALLOWED_ORIGINS, DB_PATH
from .db import fetch_all, fetch_one
from .migration import migrate
from .parts import normalize_part_number
from .privacy import mask_vin, validate_vin
from .schemas import OrderCreate, VINDecodeRequest
from .services import list_products, get_product, create_order

app = FastAPI(title="PartsHub API", version=APP_VERSION, openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs", redoc_url="/api/v1/redoc")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=False, allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])
migrate(DB_PATH)


def envelope(data, *, source=None, verification_status="", confidence_score=0, last_updated_at=""):
    return {"data": data, "meta": {"source": source or [], "verification_status": verification_status,
            "confidence_score": confidence_score, "last_updated_at": last_updated_at, "api_version": "v1"}, "errors": []}

@app.get("/api/v1/health")
def health():
    return {"status":"ok","version":APP_VERSION}


@app.get("/docs", include_in_schema=False)
def legacy_docs():
    return RedirectResponse("/api/v1/docs")

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


@app.get("/api/v1/parts/{part_number}")
def part_by_number(part_number: str):
    normalized = normalize_part_number(part_number)
    part = fetch_one("SELECT * FROM parts WHERE normalized_part_number=?", (normalized,))
    if not part:
        part = fetch_one("SELECT p.* FROM parts p JOIN part_number_aliases a ON a.part_id=p.id WHERE a.normalized_alias=?", (normalized,))
    if not part:
        raise HTTPException(status_code=404, detail="找不到零件料號")
    product_id = part.get("product_id")
    if product_id:
        product = fetch_one("SELECT price_twd, status, source_url FROM products WHERE id=?", (product_id,))
        if product:
            part["product"] = product
    return envelope(part, source=["PartsHub domain database"], verification_status=part["verification_status"],
                    confidence_score=part["confidence_score"], last_updated_at=part["updated_at"])


@app.get("/api/v1/parts/{part_number}/fitments")
def part_fitments(part_number: str):
    normalized = normalize_part_number(part_number)
    rows = fetch_all("""SELECT f.*, v.make, v.brand, v.model, v.generation, v.chassis_code, v.engine_name
        FROM part_vehicle_fitments f JOIN parts p ON p.id=f.part_id JOIN vehicles v ON v.id=f.vehicle_id
        WHERE p.normalized_part_number=? ORDER BY v.model_year_start, v.model""", (normalized,))
    return envelope({"items": rows, "count": len(rows)}, source=["PartsHub domain database"])


@app.get("/api/v1/parts/{part_number}/supersessions")
def part_supersessions(part_number: str):
    normalized = normalize_part_number(part_number)
    rows = fetch_all("""SELECT s.*, old.normalized_part_number old_part_number, new.normalized_part_number new_part_number
        FROM part_supersessions s JOIN parts old ON old.id=s.old_part_id JOIN parts new ON new.id=s.new_part_id
        WHERE old.normalized_part_number=? OR new.normalized_part_number=?""", (normalized, normalized))
    return envelope({"items": rows, "count": len(rows)}, source=["PartsHub domain database"])


@app.get("/api/v1/parts/{part_number}/alternatives")
def part_alternatives(part_number: str):
    normalized = normalize_part_number(part_number)
    rows = fetch_all("""SELECT a.alias_part_number, a.alias_type, a.brand, a.verified, p.normalized_part_number
        FROM part_number_aliases a JOIN parts p ON p.id=a.part_id WHERE p.normalized_part_number=?""", (normalized,))
    return envelope({"items": rows, "count": len(rows)}, source=["PartsHub domain database"])


@app.get("/api/v1/vehicles")
def vehicles(make: str = "", model: str = "", year: int | None = None):
    clauses, params = [], []
    if make.strip(): clauses.append("make LIKE ?"); params.append(f"%{make.strip()}%")
    if model.strip(): clauses.append("model LIKE ?"); params.append(f"%{model.strip()}%")
    if year is not None: clauses.append("model_year_start<=? AND model_year_end>=?"); params.extend([year, year])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = fetch_all(f"SELECT * FROM vehicles {where} ORDER BY make,model,model_year_start", tuple(params))
    return envelope({"items": rows, "count": len(rows)}, source=["PartsHub domain database"])


@app.get("/api/v1/vehicles/{vehicle_id}/parts")
def vehicle_parts(vehicle_id: int):
    rows = fetch_all("""SELECT p.*, f.fitment_status, f.confidence_score, f.verification_status
        FROM part_vehicle_fitments f JOIN parts p ON p.id=f.part_id WHERE f.vehicle_id=? ORDER BY p.part_name_zh""", (vehicle_id,))
    return envelope({"items": rows, "count": len(rows)}, source=["PartsHub domain database"])


@app.get("/api/v1/obd/{code}")
def obd(code: str):
    item = fetch_one("SELECT * FROM diagnostic_codes WHERE code=?", (code.upper(),))
    if not item: raise HTTPException(status_code=404, detail="找不到故障碼")
    return envelope(item, source=[item.get("source")], verification_status="verified" if item["verified"] else "unverified")


@app.get("/api/v1/knowledge/{slug}")
def knowledge(slug: str):
    item = fetch_one("SELECT * FROM knowledge_articles WHERE slug=? AND verification_status IN ('published','demo')", (slug,))
    if not item: raise HTTPException(status_code=404, detail="找不到知識文章")
    return envelope(item, source=json.loads(item["source_references"] or "[]") if item.get("source_references") else [])


@app.get("/api/v1/search")
def search(q: str = Query(min_length=1, max_length=120)):
    normalized = normalize_part_number(q)
    like = f"%{q.strip()}%"
    rows = fetch_all("""SELECT p.*, CASE WHEN p.normalized_part_number=? THEN 0
        WHEN p.normalized_part_number LIKE ? THEN 1 ELSE 2 END AS rank
        FROM parts p LEFT JOIN part_number_aliases a ON a.part_id=p.id
        WHERE p.normalized_part_number=? OR p.normalized_part_number LIKE ? OR p.part_name_zh LIKE ?
           OR p.part_name_en LIKE ? OR a.normalized_alias=? OR a.alias_part_number LIKE ?
        GROUP BY p.id ORDER BY rank,p.part_name_zh LIMIT 50""",
        (normalized, f"%{normalized}%", normalized, f"%{normalized}%", like, like, normalized, like))
    return envelope({"items": rows, "count": len(rows)}, source=["PartsHub domain database"])


@app.post("/api/v1/vin/decode")
def vin_decode(payload: VINDecodeRequest, request: Request):
    try:
        vin = validate_vin(payload.vin)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    masked = mask_vin(vin)
    # Provider abstraction is intentionally explicit until a licensed VIN source is connected.
    return envelope({"masked_vin": masked, "provider": "unavailable", "verified": False,
                     "confidence_score": 0, "status": "manual_selection_required",
                     "message": "尚未串接授權 VIN provider，請改用手動選車。"},
                    source=["No licensed VIN provider configured"], verification_status="unverified", confidence_score=0)
