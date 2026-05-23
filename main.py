from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

import auth_utils
import database
import models
from product_options import PRODUCT_CATEGORIES
from routers import auth, barter, feedback, products, search, seller


models.Base.metadata.create_all(bind=database.engine)


def ensure_barter_schema():
    inspector = inspect(database.engine)
    columns = [column["name"] for column in inspector.get_columns("barter_swipes")]
    if "offered_product_id" not in columns:
        with database.engine.begin() as conn:
            conn.execute(text("ALTER TABLE barter_swipes ADD COLUMN offered_product_id INTEGER"))


def ensure_product_image_schema():
    """補上圖片存進資料庫需要的欄位。

    SQLAlchemy 的 create_all 只會建立新資料表，不會自動替既有資料表新增欄位。
    因此部署到 Render PostgreSQL 或沿用本機 SQLite 時，用這個小型遷移補齊欄位。
    """
    inspector = inspect(database.engine)
    columns = [column["name"] for column in inspector.get_columns("products")]
    dialect = database.engine.dialect.name
    image_data_type = "BYTEA" if dialect == "postgresql" else "BLOB"

    alter_statements = []
    if "image_data" not in columns:
        alter_statements.append(f"ALTER TABLE products ADD COLUMN image_data {image_data_type}")
    if "image_mime" not in columns:
        alter_statements.append("ALTER TABLE products ADD COLUMN image_mime VARCHAR")
    if "image_filename" not in columns:
        alter_statements.append("ALTER TABLE products ADD COLUMN image_filename VARCHAR")

    if alter_statements:
        with database.engine.begin() as conn:
            for statement in alter_statements:
                conn.execute(text(statement))


ensure_barter_schema()
ensure_product_image_schema()

app = FastAPI(title="興大校園二手市集")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(products.router)
app.include_router(search.router)
app.include_router(feedback.router)
app.include_router(seller.router)
app.include_router(auth.router)
app.include_router(barter.router)


def get_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        token = token.replace("Bearer ", "")
        return jwt.decode(token, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
    except Exception:
        return None


@app.get("/")
def read_root(request: Request, db: Session = Depends(database.get_db)):
    user = get_user_from_cookie(request)
    recent_products = db.query(models.Product).order_by(models.Product.id.desc()).limit(6).all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": recent_products,
            "user": user,
            "categories": PRODUCT_CATEGORIES,
        },
    )


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/post")
def post_page(request: Request):
    user = get_user_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "post.html",
        {"request": request, "user": user, "categories": PRODUCT_CATEGORIES},
    )


@app.get("/contact")
def contact_page(request: Request):
    user = get_user_from_cookie(request)
    return templates.TemplateResponse("contact.html", {"request": request, "user": user})
