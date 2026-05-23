from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from jose import jwt
import models, database, auth_utils

router = APIRouter(prefix="/seller", tags=["seller"])
templates = Jinja2Templates(directory="templates")

@router.get("/dashboard")
def seller_dashboard(request: Request, db: Session = Depends(database.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("login.html", {"request": request, "error": "請先登入"})

    try:
        token_str = token.replace("Bearer ", "")
        payload = jwt.decode(token_str, auth_utils.SECRET_KEY, algorithms=[auth_utils.ALGORITHM])
        user_id = payload.get("user_id")
        
        # 只顯示該使用者的商品
        my_products = db.query(models.Product).filter(models.Product.owner_id == user_id).all()
        
        return templates.TemplateResponse("seller_dashboard.html", {
            "request": request, 
            "my_products": my_products,
            "user": payload
        })
    except:
        return templates.TemplateResponse("login.html", {"request": request, "error": "工作階段過期，請重新登入"})