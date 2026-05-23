# campus-market-try

興大校園二手市集 FastAPI 專案。

## 本機執行

沒有設定 `DATABASE_URL` 時，專案會自動使用 SQLite：

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Render PostgreSQL 設定

1. 在 Render 建立 PostgreSQL 資料庫。
2. 複製資料庫的 Internal Database URL。
3. 到 Web Service 的 Environment Variables 新增：

```text
Key: DATABASE_URL
Value: 貼上 Internal Database URL
```

4. Web Service 設定：

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

## 資料庫切換方式

專案會依照 `DATABASE_URL` 自動切換：

```text
有 DATABASE_URL    → 使用 PostgreSQL
沒有 DATABASE_URL  → 使用 SQLite
```

`.env` 不要推上 GitHub，真正的資料庫密碼請放在 Render Environment Variables。

## 商品照片儲存方式

此版本已改成把商品照片直接存進資料庫：

```text
products.image_data      圖片二進位資料，PostgreSQL 會使用 BYTEA
products.image_mime      圖片 MIME 類型，例如 image/jpeg、image/png
products.image_filename  原始檔名
products.image           圖片讀取網址，例如 /products/1/image
```

上傳商品時，FastAPI 會讀取圖片內容並存入 PostgreSQL。瀏覽商品時，前端會透過：

```text
/products/{product_id}/image
```

從資料庫讀出圖片並顯示。

目前圖片限制為 5MB，避免免費資料庫容量太快被照片塞滿。
