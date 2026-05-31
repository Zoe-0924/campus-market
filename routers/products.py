from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy.orm import Session

import auth_utils
import database
import models
from product_options import PRODUCT_CATEGORIES


router = APIRouter(prefix="/products", tags=["products"])
templates = Jinja2Templates(directory="templates")


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


MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB，避免 Render Free PostgreSQL 被圖片塞爆。


async def read_image_upload(file: UploadFile):
    """讀取上傳圖片，回傳可存進 PostgreSQL BYTEA / SQLite BLOB 的資料。"""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="請上傳商品照片")

    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只允許上傳圖片檔案")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="圖片檔案不可為空")
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="圖片不可超過 5MB")

    return data, content_type, file.filename


def product_image_path(product_id: int) -> str:
    return f"/products/{product_id}/image"


@router.get("/")
def get_products(request: Request, category: str = None, db: Session = Depends(database.get_db)):
    user = get_current_user(request)
    query = db.query(models.Product)
    if category:
        query = query.filter(models.Product.category == category)
    products = query.all()
    return templates.TemplateResponse(
        "category.html",
        {
            "request": request,
            "products": products,
            "current_category": category or "全部商品",
            "user": user,
            "categories": PRODUCT_CATEGORIES,
        },
    )


@router.get("/{product_id}/image")
def get_product_image(product_id: int, db: Session = Depends(database.get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product or not product.image_data:
        raise HTTPException(status_code=404, detail="找不到商品圖片")

    return Response(
        content=product.image_data,
        media_type=product.image_mime or "image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/{product_id}")
def get_product_detail(request: Request, product_id: int, db: Session = Depends(database.get_db)):
    user = get_current_user(request)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    return templates.TemplateResponse("detail.html", {"request": request, "product": product, "user": user})


@router.post("/")
async def create_product(
    request: Request,
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    tags: str = Form(""),
    location: str = Form(...),
    contact_type: str = Form(...),
    contact: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    image_data, image_mime, image_filename = await read_image_upload(file)

    new_product = models.Product(
        name=name,
        price=price,
        category=category,
        tags=tags,
        location=location,
        contact_type=contact_type,
        contact=contact,
        description=description,
        image_data=image_data,
        image_mime=image_mime,
        image_filename=image_filename,
        owner_id=user.get("user_id"),
    )
    db.add(new_product)
    db.flush()
    new_product.image = product_image_path(new_product.id)
    db.commit()
    return RedirectResponse(url="/seller/dashboard", status_code=303)


@router.get("/{product_id}/edit")
def edit_product_page(request: Request, product_id: int, db: Session = Depends(database.get_db)):
    user = get_current_user(request)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not user or not product or product.owner_id != user.get("user_id"):
        raise HTTPException(status_code=403, detail="權限不足")
    return templates.TemplateResponse(
        "edit.html",
        {
            "request": request,
            "product": product,
            "user": user,
            "categories": PRODUCT_CATEGORIES,
        },
    )


@router.post("/{product_id}/edit")
async def update_product(
    request: Request,
    product_id: int,
    name: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    tags: str = Form(""),
    location: str = Form(...),
    contact_type: str = Form(...),
    contact: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(None),
    db: Session = Depends(database.get_db),
):
    user = get_current_user(request)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()

    if not user or not product or product.owner_id != user.get("user_id"):
        raise HTTPException(status_code=403, detail="權限不足")

    product.name = name
    product.price = price
    product.category = category
    product.location = location
    product.tags = tags
    product.description = description
    product.contact_type = contact_type
    product.contact = contact

    if file and file.filename:
        image_data, image_mime, image_filename = await read_image_upload(file)
        product.image_data = image_data
        product.image_mime = image_mime
        product.image_filename = image_filename
        product.image = product_image_path(product.id)

    db.commit()
    return RedirectResponse(url="/seller/dashboard", status_code=303)


@router.post("/{product_id}/delete")
def delete_product(request: Request, product_id: int, db: Session = Depends(database.get_db)):
    user = get_current_user(request)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not user or not product or product.owner_id != user.get("user_id"):
        raise HTTPException(status_code=403, detail="權限不足")
    db.delete(product)
    db.commit()
    return RedirectResponse(url="/seller/dashboard", status_code=303)
