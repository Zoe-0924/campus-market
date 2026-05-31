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

# ----------------- MONKEY PATCH JINJA2TEMPLATES GLOBALS -----------------
def get_user_avatar(user_id: int):
    if not user_id:
        return None
    db = database.SessionLocal()
    try:
        u = db.query(models.User).filter(models.User.id == user_id).first()
        return u.avatar if u else None
    finally:
        db.close()

def get_user_nickname(user_id: int):
    if not user_id:
        return None
    db = database.SessionLocal()
    try:
        u = db.query(models.User).filter(models.User.id == user_id).first()
        if u:
            return u.nickname or u.username
        return None
    finally:
        db.close()

original_init = Jinja2Templates.__init__
def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    self.env.globals.update(
        get_user_avatar=get_user_avatar,
        get_user_nickname=get_user_nickname
    )
Jinja2Templates.__init__ = patched_init
# -----------------------------------------------------------------------

from product_options import PRODUCT_CATEGORIES
from routers import auth, barter, feedback, products, search, seller, chat, settings


models.Base.metadata.create_all(bind=database.engine)


def db_dialect_name():
    return database.engine.dialect.name


def binary_column_type():
    return "BYTEA" if db_dialect_name() == "postgresql" else "BLOB"


def boolean_default_value():
    return "false" if db_dialect_name() == "postgresql" else "0"


def ensure_barter_schema():
    inspector = inspect(database.engine)
    if not inspector.has_table("barter_swipes"):
        return
    columns = [column["name"] for column in inspector.get_columns("barter_swipes")]
    if "offered_product_id" not in columns:
        with database.engine.begin() as conn:
            conn.execute(text("ALTER TABLE barter_swipes ADD COLUMN offered_product_id INTEGER"))


ensure_barter_schema()


def ensure_product_image_schema():
    inspector = inspect(database.engine)
    if not inspector.has_table("products"):
        return
    columns = [column["name"] for column in inspector.get_columns("products")]
    with database.engine.begin() as conn:
        if "image_data" not in columns:
            conn.execute(text(f"ALTER TABLE products ADD COLUMN image_data {binary_column_type()}"))
        if "image_mime" not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN image_mime VARCHAR"))
        if "image_filename" not in columns:
            conn.execute(text("ALTER TABLE products ADD COLUMN image_filename VARCHAR"))


ensure_product_image_schema()


def ensure_user_profile_schema():
    inspector = inspect(database.engine)
    if not inspector.has_table("users"):
        return
    columns = [column["name"] for column in inspector.get_columns("users")]
    with database.engine.begin() as conn:
        if "nickname" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN nickname VARCHAR"))
        if "avatar" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar VARCHAR"))
        if "avatar_data" not in columns:
            conn.execute(text(f"ALTER TABLE users ADD COLUMN avatar_data {binary_column_type()}"))
        if "avatar_mime" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_mime VARCHAR"))
        if "avatar_filename" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_filename VARCHAR"))
        if "bio" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN bio TEXT"))


ensure_user_profile_schema()


def ensure_chat_room_status_schema():
    inspector = inspect(database.engine)
    if not inspector.has_table("chat_rooms"):
        return
    columns = [column["name"] for column in inspector.get_columns("chat_rooms")]
    bool_default = boolean_default_value()
    with database.engine.begin() as conn:
        if "buyer_archived" not in columns:
            conn.execute(text(f"ALTER TABLE chat_rooms ADD COLUMN buyer_archived BOOLEAN DEFAULT {bool_default}"))
        if "seller_archived" not in columns:
            conn.execute(text(f"ALTER TABLE chat_rooms ADD COLUMN seller_archived BOOLEAN DEFAULT {bool_default}"))
        if "buyer_deleted" not in columns:
            conn.execute(text(f"ALTER TABLE chat_rooms ADD COLUMN buyer_deleted BOOLEAN DEFAULT {bool_default}"))
        if "seller_deleted" not in columns:
            conn.execute(text(f"ALTER TABLE chat_rooms ADD COLUMN seller_deleted BOOLEAN DEFAULT {bool_default}"))
        if "is_blocked" not in columns:
            conn.execute(text(f"ALTER TABLE chat_rooms ADD COLUMN is_blocked BOOLEAN DEFAULT {bool_default}"))
        
        # Migrate data from is_archived to buyer_archived and seller_archived if is_archived exists
        if "is_archived" in columns:
            conn.execute(text("UPDATE chat_rooms SET buyer_archived = is_archived, seller_archived = is_archived"))


ensure_chat_room_status_schema()

app = FastAPI(title="興大校園二手市集")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(products.router)
app.include_router(search.router)
app.include_router(feedback.router)
app.include_router(seller.router)
app.include_router(auth.router)
app.include_router(barter.router)
app.include_router(chat.router)
app.include_router(settings.router)


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


@app.get("/help")
def help_page(request: Request):
    user = get_user_from_cookie(request)
    return templates.TemplateResponse("help.html", {"request": request, "user": user})
