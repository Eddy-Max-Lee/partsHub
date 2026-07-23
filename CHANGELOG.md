# Changelog

## 4.0.0 — 2026-07-24

- 將前端與後端拆成獨立目錄、獨立 Docker image 與 REST API
- 後端不再提供前端 HTML
- 前台不再直接內嵌或讀取 SQLite
- 商品詳情加入原始商品頁完整相簿與縮圖切換
- 11 個商品共寫入 28 張商品圖／原廠零件分解圖 URL
- 全站改為繁體中文與新台幣計價
- 訂單金額與免運門檻改為 TWD
- 新增 FastAPI Swagger、CORS 設定、CI 與 Docker Compose
