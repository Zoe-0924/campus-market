from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy.orm import Session

import auth_utils
import database
import models
from product_options import PRODUCT_CATEGORIES


router = APIRouter(prefix="/search", tags=["search"])
templates = Jinja2Templates(directory="templates")


def parse_price(value: str):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        return jwt.decode(
            token.replace("Bearer ", ""),
            auth_utils.SECRET_KEY,
            algorithms=[auth_utils.ALGORITHM],
        )
    except Exception:
        return None


@router.get("/")
def search_products(
    request: Request,
    q: str = "",
    cat: str = "",
    min_p: str = "",
    max_p: str = "",
    db: Session = Depends(database.get_db),
):
    user = get_current_user(request)
    query = db.query(models.Product)
    min_price = parse_price(min_p)
    max_price = parse_price(max_p)
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)

    if q:
        query = query.filter(
            (models.Product.name.contains(q)) | (models.Product.tags.contains(q))
        )
    if cat:
        query = query.filter(models.Product.category == cat)

    products = query.all()
    title_parts = []
    if q:
        title_parts.append(f"關鍵字：{q}")
    if cat:
        title_parts.append(f"分類：{cat}")
    if min_price is not None and max_price is not None:
        title_parts.append(f"價格：{int(min_price)} - {int(max_price)}")
    elif min_price is not None:
        title_parts.append(f"價格：{int(min_price)} 以上")
    elif max_price is not None:
        title_parts.append(f"價格：{int(max_price)} 以下")
    title = "搜尋結果"
    if title_parts:
        title += " - " + "，".join(title_parts)

    return templates.TemplateResponse(
        "category.html",
        {
            "request": request,
            "products": products,
            "current_category": title,
            "user": user,
            "categories": PRODUCT_CATEGORIES,
        },
    )
