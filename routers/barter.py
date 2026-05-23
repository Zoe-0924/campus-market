from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional

import auth_utils
import database
import models


router = APIRouter(prefix="/barter", tags=["barter"])
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


@router.get("/")
def barter_page(
    request: Request,
    offering_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
):
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "請先登入才能使用換換模式"},
        )

    user_id = user.get("user_id")
    my_products = (
        db.query(models.Product)
        .filter(models.Product.owner_id == user_id)
        .order_by(models.Product.id.desc())
        .all()
    )

    selected_product = None
    available_products = []
    if offering_id is not None:
        selected_product = (
            db.query(models.Product)
            .filter(
                models.Product.id == offering_id,
                models.Product.owner_id == user_id,
            )
            .first()
        )
        if not selected_product:
            raise HTTPException(status_code=404, detail="找不到你要拿來交換的物品")

        swiped_ids = (
            db.query(models.BarterSwipe.target_product_id)
            .filter(
                models.BarterSwipe.user_id == user_id,
                models.BarterSwipe.offered_product_id == selected_product.id,
            )
            .all()
        )
        swiped_ids = [item[0] for item in swiped_ids]

        available_products = (
            db.query(models.Product)
            .filter(
                models.Product.owner_id != user_id,
                ~models.Product.id.in_(swiped_ids),
            )
            .order_by(func.random())
            .limit(10)
            .all()
        )

    return templates.TemplateResponse(
        "barter.html",
        {
            "request": request,
            "products": available_products,
            "my_products": my_products,
            "selected_product": selected_product,
            "user": user,
        },
    )


@router.post("/swipe/{product_id}")
async def handle_swipe(
    product_id: int,
    is_like: bool,
    offered_product_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
):
    user = get_current_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"msg": "請先登入"})

    my_id = user.get("user_id")
    offered_product = (
        db.query(models.Product)
        .filter(
            models.Product.id == offered_product_id,
            models.Product.owner_id == my_id,
        )
        .first()
    )
    if not offered_product:
        return JSONResponse(status_code=400, content={"msg": "請先選擇你要拿來交換的物品"})

    target_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not target_product:
        return JSONResponse(status_code=404, content={"msg": "找不到這個物品"})
    if target_product.owner_id == my_id:
        return JSONResponse(status_code=400, content={"msg": "不能滑自己的物品"})

    swipe = (
        db.query(models.BarterSwipe)
        .filter(
            models.BarterSwipe.user_id == my_id,
            models.BarterSwipe.offered_product_id == offered_product.id,
            models.BarterSwipe.target_product_id == target_product.id,
        )
        .first()
    )
    if swipe:
        swipe.is_like = is_like
    else:
        swipe = models.BarterSwipe(
            user_id=my_id,
            offered_product_id=offered_product.id,
            target_product_id=target_product.id,
            is_like=is_like,
        )
        db.add(swipe)
    db.commit()

    if is_like:
        reciprocal_like = (
            db.query(models.BarterSwipe)
            .filter(
                models.BarterSwipe.user_id == target_product.owner_id,
                models.BarterSwipe.offered_product_id == target_product.id,
                models.BarterSwipe.target_product_id == offered_product.id,
                models.BarterSwipe.is_like == True,
            )
            .first()
        )
        if reciprocal_like:
            return {
                "status": "match",
                "target_name": target_product.name,
                "offered_name": offered_product.name,
                "contact": target_product.contact,
            }

    return {"status": "ok"}


@router.get("/matches")
def get_matches(request: Request, db: Session = Depends(database.get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")

    my_id = user.get("user_id")
    my_likes = (
        db.query(models.BarterSwipe)
        .filter(
            models.BarterSwipe.user_id == my_id,
            models.BarterSwipe.is_like == True,
            models.BarterSwipe.offered_product_id.isnot(None),
        )
        .all()
    )

    matches = []
    seen_pairs = set()
    for swipe in my_likes:
        their_product = swipe.product
        my_product = swipe.offered_product
        if not their_product or not my_product:
            continue

        reciprocal_like = (
            db.query(models.BarterSwipe)
            .filter(
                models.BarterSwipe.user_id == their_product.owner_id,
                models.BarterSwipe.offered_product_id == their_product.id,
                models.BarterSwipe.target_product_id == my_product.id,
                models.BarterSwipe.is_like == True,
            )
            .first()
        )

        pair_key = (my_product.id, their_product.id)
        if reciprocal_like and pair_key not in seen_pairs:
            seen_pairs.add(pair_key)
            matches.append(
                {
                    "their_item": their_product,
                    "my_item": my_product,
                    "partner_name": their_product.owner.username,
                    "contact_type": their_product.contact_type,
                    "contact": their_product.contact,
                }
            )

    return templates.TemplateResponse(
        "matches.html",
        {"request": request, "matches": matches, "user": user},
    )


@router.post("/unmatch/{product_id}")
def unmatch_product(
    product_id: int,
    request: Request,
    offered_product_id: Optional[int] = None,
    db: Session = Depends(database.get_db),
):
    user = get_current_user(request)
    if not user:
        return {"status": "error", "message": "請先登入"}

    my_id = user.get("user_id")
    query = db.query(models.BarterSwipe).filter(
        models.BarterSwipe.user_id == my_id,
        models.BarterSwipe.target_product_id == product_id,
        models.BarterSwipe.is_like == True,
    )
    if offered_product_id is not None:
        query = query.filter(models.BarterSwipe.offered_product_id == offered_product_id)

    swipe_record = query.first()
    if swipe_record:
        db.delete(swipe_record)
        db.commit()
        return {"status": "ok"}

    return {"status": "error", "message": "找不到這筆配對紀錄"}
