from __future__ import annotations
import secrets
from datetime import datetime, timezone
from .db import connection, fetch_all, fetch_one

def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()

def list_products(query: str = "") -> list[dict]:
    params: list[object] = []
    where = ""
    if query.strip():
        q = f"%{query.strip()}%"
        where = "WHERE p.name_zh LIKE ? OR p.name_en LIKE ? OR p.part_number LIKE ?"
        params.extend([q, q, q])
    products = fetch_all(f"SELECT p.* FROM products p {where} ORDER BY p.id", tuple(params))
    if not products:
        return []
    ids = [p["id"] for p in products]
    marks = ",".join("?" for _ in ids)
    images = fetch_all(f"SELECT * FROM product_images WHERE product_id IN ({marks}) ORDER BY product_id,sort_order,id", tuple(ids))
    by_product: dict[int, list[dict]] = {pid: [] for pid in ids}
    for image in images:
        by_product[image["product_id"]].append(image)
    for p in products:
        p["gallery"] = by_product[p["id"]]
        p["primary_image"] = p["gallery"][0]["source_url"] if p["gallery"] else None
    return products

def get_product(product_id: int) -> dict | None:
    product = fetch_one("SELECT * FROM products WHERE id=?", (product_id,))
    if not product:
        return None
    product["gallery"] = fetch_all("SELECT * FROM product_images WHERE product_id=? ORDER BY sort_order,id", (product_id,))
    product["primary_image"] = product["gallery"][0]["source_url"] if product["gallery"] else None
    return product

def create_order(items: list[dict]) -> dict:
    if not items:
        raise ValueError("購物車是空的")
    quantities: dict[int,int] = {}
    for item in items:
        pid=int(item["product_id"]); qty=max(1,min(99,int(item["quantity"])))
        quantities[pid]=quantities.get(pid,0)+qty
    marks=','.join('?' for _ in quantities)
    with connection() as con:
        rows=con.execute(f"SELECT id,part_number,name_zh,price_twd FROM products WHERE id IN ({marks})",tuple(quantities)).fetchall()
        data={int(r['id']):dict(r) for r in rows}
        if len(data)!=len(quantities): raise ValueError("部分商品已不存在")
        subtotal=sum(int(data[pid]['price_twd']) * qty for pid,qty in quantities.items())
        shipping=0 if subtotal>=3000 else 120
        total=subtotal+shipping
        number='TW'+datetime.now().strftime('%y%m%d')+secrets.token_hex(2).upper()
        cur=con.execute("INSERT INTO orders(order_number,currency,subtotal,shipping,total,status,created_at) VALUES(?,?,?,?,?,?,?)",(number,'TWD',subtotal,shipping,total,'demo_created',utcnow()))
        oid=cur.lastrowid
        for pid,qty in quantities.items():
            p=data[pid]; line=int(p['price_twd'])*qty
            con.execute("INSERT INTO order_items(order_id,product_id,part_number,product_name,unit_price,quantity,line_total) VALUES(?,?,?,?,?,?,?)",(oid,pid,p['part_number'],p['name_zh'],p['price_twd'],qty,line))
    return {'order_number':number,'currency':'TWD','subtotal':subtotal,'shipping':shipping,'total':total,'status':'demo_created'}
