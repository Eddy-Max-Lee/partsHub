from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .parts import normalize_part_number


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


DOMAIN_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY, applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT, make TEXT NOT NULL, brand TEXT NOT NULL,
    model TEXT NOT NULL, generation TEXT, chassis_code TEXT, model_year_start INTEGER,
    model_year_end INTEGER, production_date_start TEXT, production_date_end TEXT,
    body_style TEXT, engine_code TEXT, engine_name TEXT, displacement TEXT,
    fuel_type TEXT, transmission_code TEXT, transmission_type TEXT, drive_type TEXT,
    market TEXT, steering_position TEXT, trim TEXT, platform TEXT, notes TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    UNIQUE(make, model, generation, engine_code, model_year_start)
);
CREATE TABLE IF NOT EXISTS vin_decode_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT, vin_hash TEXT NOT NULL, masked_vin TEXT NOT NULL,
    wmi TEXT, vds TEXT, vis TEXT, manufacturer TEXT, make TEXT, model TEXT,
    model_year INTEGER, production_plant TEXT, serial_number TEXT, engine_code TEXT,
    transmission_code TEXT, body_style TEXT, market TEXT, raw_response TEXT,
    provider TEXT NOT NULL, confidence_score REAL NOT NULL DEFAULT 0,
    verified INTEGER NOT NULL DEFAULT 0, decoded_at TEXT, created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER UNIQUE REFERENCES products(id),
    normalized_part_number TEXT UNIQUE NOT NULL, display_part_number TEXT NOT NULL,
    manufacturer TEXT, brand TEXT, part_name_zh TEXT NOT NULL, part_name_en TEXT,
    category_id TEXT, description_short TEXT, description_full TEXT,
    function_description TEXT, installation_location TEXT, failure_symptoms TEXT,
    diagnostic_notes TEXT, replacement_interval TEXT, installation_difficulty TEXT,
    estimated_installation_time TEXT, required_tools TEXT, torque_specifications TEXT,
    dimensions TEXT, weight TEXT, material TEXT, country_of_origin TEXT,
    safety_critical INTEGER NOT NULL DEFAULT 0, hazardous_shipping INTEGER NOT NULL DEFAULT 0,
    return_restricted INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'draft',
    source_type TEXT NOT NULL DEFAULT 'crawled', verification_status TEXT NOT NULL DEFAULT 'unverified',
    confidence_score REAL NOT NULL DEFAULT 0, published_at TEXT, last_verified_at TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS part_number_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT, part_id INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    alias_part_number TEXT NOT NULL, normalized_alias TEXT NOT NULL, alias_type TEXT NOT NULL,
    brand TEXT, manufacturer TEXT, market TEXT, source TEXT, verified INTEGER NOT NULL DEFAULT 0, notes TEXT,
    UNIQUE(part_id, normalized_alias)
);
CREATE TABLE IF NOT EXISTS part_supersessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, old_part_id INTEGER NOT NULL REFERENCES parts(id),
    new_part_id INTEGER NOT NULL REFERENCES parts(id), supersession_type TEXT NOT NULL,
    effective_date TEXT, compatibility_notes TEXT, additional_parts_required TEXT,
    coding_required INTEGER NOT NULL DEFAULT 0, source TEXT, verified INTEGER NOT NULL DEFAULT 0,
    UNIQUE(old_part_id, new_part_id)
);
CREATE TABLE IF NOT EXISTS part_vehicle_fitments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, part_id INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE, fitment_status TEXT NOT NULL,
    model_year_start INTEGER, model_year_end INTEGER, production_date_start TEXT,
    production_date_end TEXT, engine_code TEXT, transmission_code TEXT, drive_type TEXT,
    market TEXT, trim TEXT, vin_range_start TEXT, vin_range_end TEXT, option_codes TEXT,
    exclusions TEXT, installation_notes TEXT, source TEXT, confidence_score REAL NOT NULL DEFAULT 0,
    verification_status TEXT NOT NULL DEFAULT 'unverified', last_verified_at TEXT
);
CREATE TABLE IF NOT EXISTS part_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT, part_id INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL, file_url TEXT NOT NULL, thumbnail_url TEXT, alt_text TEXT,
    caption TEXT, copyright_owner TEXT, license_type TEXT, source_url TEXT, sort_order INTEGER NOT NULL DEFAULT 0,
    verified INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS knowledge_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT UNIQUE NOT NULL, title TEXT NOT NULL,
    excerpt TEXT NOT NULL, body TEXT NOT NULL, category TEXT NOT NULL, author TEXT,
    reviewer TEXT, source_references TEXT, verification_status TEXT NOT NULL DEFAULT 'draft',
    published_at TEXT, updated_at TEXT NOT NULL, last_reviewed_at TEXT, seo_title TEXT,
    seo_description TEXT, canonical_url TEXT
);
CREATE TABLE IF NOT EXISTS diagnostic_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, system TEXT NOT NULL,
    title_zh TEXT NOT NULL, title_en TEXT, description TEXT NOT NULL, possible_causes TEXT,
    diagnostic_steps TEXT, severity TEXT, driveability_warning TEXT, source TEXT,
    verified INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, source_url TEXT,
    authorization_status TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS product_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT, part_id INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id), sku TEXT, condition TEXT NOT NULL,
    packaging_type TEXT, stock_status TEXT, stock_quantity INTEGER, lead_time_days INTEGER,
    supplier_price REAL, landed_cost REAL, retail_price REAL, currency TEXT NOT NULL DEFAULT 'TWD',
    shipping_class TEXT, return_policy TEXT, warranty TEXT, source_url TEXT, last_synced_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_parts_normalized_number ON parts(normalized_part_number);
CREATE INDEX IF NOT EXISTS idx_aliases_normalized_number ON part_number_aliases(normalized_alias);
CREATE INDEX IF NOT EXISTS idx_fitments_vehicle ON part_vehicle_fitments(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_fitments_part ON part_vehicle_fitments(part_id);
"""


def seed_demo(con: sqlite3.Connection) -> None:
    timestamp = now()
    products = con.execute("SELECT id, part_number, name_zh, name_en, category_zh, description_zh FROM products ORDER BY id").fetchall()
    for product in products:
        normalized = normalize_part_number(product[1])
        con.execute(
            """INSERT INTO parts(product_id, normalized_part_number, display_part_number, part_name_zh, part_name_en,
               category_id, description_short, status, source_type, verification_status, confidence_score, created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET updated_at=excluded.updated_at""",
            (product[0], normalized, product[1], product[2], product[3], product[4] or "未分類", product[5] or "",
             "published", "crawled", "unverified", 0.5, timestamp, timestamp),
        )
    vehicles = [
        ("Audi", "Audi", "A6", "C6", "4F", 2004, 2008, "BPJ", "2.0T", "汽油", "自排", "前輪", "TW"),
        ("Audi", "Audi", "A8", "D3", "4E", 2004, 2009, "BFL", "4.2L V8", "汽油", "自排", "四輪", "TW"),
        ("Audi", "Audi", "S4", "B7", "8E", 2005, 2008, "BBK", "4.2L V8", "汽油", "手排", "四輪", "EU"),
        ("BMW", "BMW", "3 Series", "E90", "E90", 2005, 2011, "N46B20", "2.0L", "汽油", "自排", "後輪", "TW"),
        ("BMW", "BMW", "5 Series", "E60", "E60", 2004, 2010, "M54B30", "3.0L", "汽油", "自排", "後輪", "TW"),
    ]
    for make, brand, model, generation, chassis, ys, ye, engine, engine_name, fuel, transmission, drive, market in vehicles:
        con.execute(
            """INSERT OR IGNORE INTO vehicles(make,brand,model,generation,chassis_code,model_year_start,model_year_end,
               engine_code,engine_name,fuel_type,transmission_type,drive_type,market,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (make, brand, model, generation, chassis, ys, ye, engine, engine_name, fuel, transmission, drive, market, timestamp, timestamp),
        )
    part_ids = [row[0] for row in con.execute("SELECT id FROM parts ORDER BY id").fetchall()]
    product_columns = {row[1] for row in con.execute("PRAGMA table_info(products)").fetchall()}
    for product_id, part_id in con.execute("SELECT product_id, id FROM parts WHERE product_id IS NOT NULL ORDER BY id").fetchall():
        replaces = con.execute("SELECT replaces FROM products WHERE id=?", (product_id,)).fetchone()[0] if "replaces" in product_columns else ""
        for alias in (replaces or "").split(",")[:3]:
            alias = alias.strip()
            if alias:
                con.execute("""INSERT OR IGNORE INTO part_number_aliases(part_id,alias_part_number,normalized_alias,alias_type,source,verified)
                    VALUES(?,?,?,?,?,?)""", (part_id, alias, normalize_part_number(alias), "replacement", "crawled product record", 0))
    for old_part_id, new_part_id in zip(part_ids[:3], part_ids[1:4]):
        con.execute("""INSERT OR IGNORE INTO part_supersessions(old_part_id,new_part_id,supersession_type,compatibility_notes,source,verified)
            VALUES(?,?,?,?,?,?)""", (old_part_id, new_part_id, "demo_replacement", "Demo 資料，需依車型與原車料號確認。", "demo seed", 0))
    vehicle_ids = [row[0] for row in con.execute("SELECT id FROM vehicles ORDER BY id").fetchall()]
    for index, part_id in enumerate(part_ids):
        for vehicle_id in vehicle_ids[:3]:
            con.execute("""INSERT OR IGNORE INTO part_vehicle_fitments(part_id,vehicle_id,fitment_status,source,confidence_score,verification_status,last_verified_at)
                VALUES(?,?,?,?,?,?,?)""", (part_id, vehicle_id, "likely", "demo seed", 0.65, "unverified", timestamp))
    articles = [
        ("how-to-read-part-number", "如何閱讀汽車零件料號", "說明原廠、OEM 與副廠料號的基本差異。", "料號教學"),
        ("genuine-oem-aftermarket", "Genuine、OEM、Aftermarket 有什麼不同？", "購買零件前理解商品條件與保固差異。", "零件知識"),
        ("vin-fitment-limitations", "VIN 適配查詢的限制", "VIN 只能作為初步篩選，仍需核對生產日期與選配。", "VIN 教學"),
        ("engine-misfire-checklist", "引擎抖動的檢查順序", "從故障碼、點火、進氣與燃油系統逐步排查。", "故障診斷"),
        ("brake-noise-safety", "煞車異音的安全提醒", "煞車系統應由專業技師檢查，不宜只依症狀購買零件。", "安裝與維修"),
    ]
    for slug, title, excerpt, category in articles:
        con.execute("""INSERT OR IGNORE INTO knowledge_articles(slug,title,excerpt,body,category,author,verification_status,updated_at,seo_title,seo_description)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (slug, title, excerpt, f"{excerpt}\n\n資料仍需依車型與來源確認。", category, "PartsHub 編輯部", "demo", timestamp, title, excerpt))
    codes = [
        ("P0300", "引擎", "隨機／多缸失火偵測", "Random/Multiple Cylinder Misfire Detected", "系統偵測到失火，不代表單一零件已損壞。"),
        ("P0171", "燃油", "系統過稀", "System Too Lean", "可能涉及進氣洩漏、燃油供應或感知器。"),
        ("P0420", "排放", "觸媒轉換效率低於門檻", "Catalyst System Efficiency Below Threshold", "應先確認排氣洩漏與感知器資料。"),
        ("P0455", "蒸發排放", "蒸發排放系統大型洩漏", "EVAP System Large Leak", "先檢查油箱蓋、管路與蒸發系統。"),
        ("P0016", "引擎正時", "曲軸與凸輪軸位置關係不正確", "Crankshaft/Camshaft Correlation", "可能需要檢查正時與感知器訊號。"),
    ]
    for code, system, title_zh, title_en, description in codes:
        con.execute("""INSERT OR IGNORE INTO diagnostic_codes(code,system,title_zh,title_en,description,possible_causes,diagnostic_steps,severity,driveability_warning,source,verified)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (code, system, title_zh, title_en, description, "需依車型與量測資料判斷", "讀取即時數據並完成基本檢查", "medium", "如有抖動、過熱或煞車異常，請停止駕駛並尋求專業協助。", "demo seed", 0))
    con.execute("INSERT OR IGNORE INTO suppliers(name,source_url,authorization_status,notes) VALUES('PartsHub Demo Supplier','https://example.test','demo','非正式供應商資料')")
    supplier_id = con.execute("SELECT id FROM suppliers WHERE name='PartsHub Demo Supplier'").fetchone()[0]
    for part_id in part_ids[:2]:
        con.execute("""INSERT OR IGNORE INTO product_offers(part_id,supplier_id,sku,condition,stock_status,stock_quantity,lead_time_days,retail_price,currency,source_url,last_synced_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (part_id, supplier_id, f"DEMO-{part_id}", "aftermarket", "demo", 5, 7, 1200, "TWD", "https://example.test", timestamp))


def migrate(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(DOMAIN_SCHEMA)
    con.execute("""DELETE FROM part_vehicle_fitments WHERE id NOT IN
        (SELECT MIN(id) FROM part_vehicle_fitments GROUP BY part_id, vehicle_id, fitment_status)""")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_fitment_part_vehicle_status ON part_vehicle_fitments(part_id, vehicle_id, fitment_status)")
    con.execute("""DELETE FROM product_offers WHERE id NOT IN
        (SELECT MIN(id) FROM product_offers GROUP BY part_id, supplier_id, COALESCE(sku, ''))""")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_offer_part_supplier_sku ON product_offers(part_id, supplier_id, sku)")
    seed_demo(con)
    con.execute("INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES('001-domain-foundation', ?)", (now(),))
    con.commit()
    con.close()
