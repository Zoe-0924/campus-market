# 興大校園二手市集

此版本保留新版頁面、聊天室、設定頁與排版，並加入 PostgreSQL / Render 支援。

## 本機啟動

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

沒有設定 `DATABASE_URL` 時，會自動使用本機 SQLite：`campus_market.db`。

## Render 部署

Web Service 設定：

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Environment Variables 請新增：

```text
Key: DATABASE_URL
Value: Render PostgreSQL 的 Internal Database URL
```

## 圖片儲存方式

商品圖片會存進資料庫：

- PostgreSQL：`BYTEA`
- SQLite：`BLOB`

商品圖片讀取路由：

```text
/products/{product_id}/image
```

使用者頭像也會存進資料庫，讀取路由：

```text
/settings/avatar/{user_id}
```

`.env`、`campus_market.db`、`static/uploads/` 不建議推上 GitHub。

## WebSocket / 聊天室部署提醒

聊天室需要 WebSocket 支援。`requirements.txt` 已改用：

```txt
uvicorn[standard]==0.41.0
```

如果 Render log 出現 `Unsupported upgrade request` 或 `No supported WebSocket library detected`，請確認 Render 有重新部署最新 commit，並確認 Build Command 是：

```bash
pip install -r requirements.txt
```

Start Command 維持：

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```
