# PartsHub v4.0.0

台灣版 OEM 汽車零件資料平台 Demo。這一版完成真正的前後端解耦、繁體中文介面、TWD 計價，以及商品詳情的原始頁面相簿／零件分解圖。

## 架構

```text
OEM 商品頁 → backend/crawler.py → SQLite
                                  ↓
frontend SPA ← REST API ← FastAPI backend
```

- `frontend/`：純靜態 SPA，只透過 HTTP API 取資料，不讀取 SQLite、不 import 後端程式。
- `backend/`：FastAPI、爬蟲、SQLite 與訂單邏輯，不提供或渲染前端 HTML。
- `preview.html`：僅供 ChatGPT 檔案預覽的資料快照，不是正式部署入口。

## 台灣化

- 語言：繁體中文 `zh-TW`
- 幣別：新台幣 `TWD`
- Demo 換算匯率：`1 USD = NT$ 32.3582`
- 匯率時間：`2026-07-23T15:17:00+00:00`
- 商品售價四捨五入至新台幣整數；正式商用應另接即時匯率、成本、稅金與利潤規則。

## 商品相簿

目前 11 個商品都存有 2–3 張原始商品頁圖片 URL，包含：

- 商品產品圖
- 原廠零件圖
- 原廠零件分解圖

前台點「查看相簿」後，可切換縮圖。資料表為 `product_images`。

## 啟動

```bash
docker compose up --build
```

- 前台：`http://localhost:8080`
- 後台資料檢視：`http://localhost:8080/admin.html`
- API：`http://localhost:8000/api/v1`
- Swagger：`http://localhost:8000/docs`

也可分開啟動：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd ../frontend
python -m http.server 8080
```

## 主要 API

- `GET /api/v1/health`
- `GET /api/v1/meta`
- `GET /api/v1/products`
- `GET /api/v1/products/{id}`
- `POST /api/v1/orders`
- `GET /api/v1/admin/products`
- `GET /api/v1/admin/source-pages`
- `GET /api/v1/admin/orders`

## 爬蟲

`backend/crawler.py` 會解析商品頁內 `cdn-product-images.revolutionparts.io` 與 `cdn-illustrations.revolutionparts.io` 圖片，將完整相簿 URL 存入 SQLite。

```bash
cd backend
python crawler.py --db data/parts.db   "https://audi.oempartsonline.com/oem-parts/audi-ignition-coil-77905115t"
```

爬蟲預設遵守 `robots.txt`，請求間隔 1.2 秒。圖片 CDN 可能拒絕伺服器端下載，因此目前以「保存來源 URL、前台直接顯示」為主。

## 資料來源與限制

Demo 資料來自公開商品頁，並非即時庫存、正式報價或台灣代理商承諾。零件是否適用仍須依 VIN、引擎代碼及底盤號確認。
