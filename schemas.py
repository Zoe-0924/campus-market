from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductCreate(BaseModel):
    name: str
    price: int
    category: str
    description: str
    contact: str
    location: str

class ProductResponse(ProductCreate):
    id: int
    image: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

class FeedbackCreate(BaseModel):
    name: str
    email: str
    message: str