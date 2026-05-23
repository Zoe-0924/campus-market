from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from typing import Optional

# 設定加密方式為 bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 加密設定 (Secret key 實務上應放在環境變數)
SECRET_KEY = "nchu_cs_project_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_password_hash(password):
    """將明文密碼轉換為雜湊值"""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """驗證密碼是否正確"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """產生 JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt