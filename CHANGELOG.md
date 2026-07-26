# Changelog

## 4.1.0 — 2026-07-26

- 新增可重複執行的 domain migration：Part、Vehicle、VIN decode result、料號別名、替代歷史、適配、知識文章、OBD、供應商報價與媒體表。
- 新增標準化料號搜尋、適配／替代／車型／OBD／知識庫 API，並統一新 API 的 `data`、`meta`、`errors` 回應格式。
- VIN 目前只做格式驗證與遮蔽，明確標示尚未串接授權 provider。
- 首頁加入 VIN 查詢入口、來源限制聲明與 JSON-LD；新增知識庫、資料政策、robots、sitemap、llms 文件。
- 相容性：既有 products、orders、product_images、爬蟲與 v4 API 保留。
- 已知限制：後台仍為檢視頁，尚未完成登入權限與完整 CRUD；公開頁面仍以靜態 SPA 為主，尚未完成全站 SSR/SSG。

## 4.0.0 — 2026-07-24

- 將前端與後端拆成獨立目錄、獨立 Docker image 與 REST API
- 後端不再提供前端 HTML
- 前台不再直接內嵌或讀取 SQLite
- 商品詳情加入原始商品頁完整相簿與縮圖切換
- 11 個商品共寫入 28 張商品圖／原廠零件分解圖 URL
- 全站改為繁體中文與新台幣計價
- 訂單金額與免運門檻改為 TWD
- 新增 FastAPI Swagger、CORS 設定、CI 與 Docker Compose
