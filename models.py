from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

    products = relationship("Product", back_populates="owner")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    category = Column(String)
    description = Column(Text)
    image = Column(String)
    image_data = Column(LargeBinary, nullable=True)
    image_mime = Column(String, nullable=True)
    image_filename = Column(String, nullable=True)
    tags = Column(String)
    location = Column(String)
    contact_type = Column(String, default="other")
    contact = Column(String)
    status = Column(String, default="上架中")
    created_at = Column(DateTime, default=datetime.now)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="products")


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class BarterSwipe(Base):
    __tablename__ = "barter_swipes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    offered_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    target_product_id = Column(Integer, ForeignKey("products.id"))
    is_like = Column(Boolean)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    product = relationship("Product", foreign_keys=[target_product_id])
    offered_product = relationship("Product", foreign_keys=[offered_product_id])
