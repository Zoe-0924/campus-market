import urllib.parse
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, Query
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from jose import jwt
from sqlalchemy.orm import Session

import auth_utils
import database
import models

router = APIRouter(prefix="/settings", tags=["settings"])
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


MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB


async def read_avatar_upload(file: UploadFile):
    if not file or not file.filename:
        return None, None, None

    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只允許上傳圖片檔案")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="圖片檔案不可為空")
    if len(data) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="頭像圖片不可超過 2MB")

    return data, content_type, file.filename


def user_avatar_path(user_id: int) -> str:
    return f"/settings/avatar/{user_id}"


@router.get("/avatar/{user_id}")
def get_avatar_image(user_id: int, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user or not db_user.avatar_data:
        raise HTTPException(status_code=404, detail="找不到頭像")

    return Response(
        content=db_user.avatar_data,
        media_type=db_user.avatar_mime or "image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("")
@router.get("/")
def settings_page(
    request: Request,
    error: str = Query(None),
    success: str = Query(None),
    db: Session = Depends(database.get_db),
    user = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_id = user.get("user_id")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "db_user": db_user,
            "error": error,
            "success": success
        }
    )


@router.post("")
@router.post("/")
async def update_settings(
    request: Request,
    nickname: str = Form(...),
    bio: str = Form(""),
    file: UploadFile = File(None),
    db: Session = Depends(database.get_db),
    user = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_id = user.get("user_id")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="找不到使用者")

    db_user.nickname = nickname.strip()
    db_user.bio = bio.strip()

    if file and file.filename:
        avatar_data, avatar_mime, avatar_filename = await read_avatar_upload(file)
        db_user.avatar_data = avatar_data
        db_user.avatar_mime = avatar_mime
        db_user.avatar_filename = avatar_filename
        db_user.avatar = user_avatar_path(user_id)

    db.commit()

    return RedirectResponse(url="/settings?success=1", status_code=303)


@router.post("/password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(database.get_db),
    user = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_id = user.get("user_id")
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="找不到使用者")

    if not auth_utils.verify_password(current_password, db_user.password_hash):
        err_msg = urllib.parse.quote("目前密碼輸入錯誤，請重新確認。")
        return RedirectResponse(url=f"/settings?error={err_msg}", status_code=303)

    if len(new_password) < 6:
        err_msg = urllib.parse.quote("新密碼長度至少需要 6 個字元。")
        return RedirectResponse(url=f"/settings?error={err_msg}", status_code=303)

    if new_password != confirm_password:
        err_msg = urllib.parse.quote("兩次輸入的新密碼不一致，請重新輸入。")
        return RedirectResponse(url=f"/settings?error={err_msg}", status_code=303)

    db_user.password_hash = auth_utils.get_password_hash(new_password)
    db.commit()

    success_msg = urllib.parse.quote("密碼已變更成功！請妥善保管您的新密碼。")
    return RedirectResponse(url=f"/settings?success={success_msg}", status_code=303)
