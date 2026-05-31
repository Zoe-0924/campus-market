from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    nickname = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    avatar_data = Column(LargeBinary, nullable=True)
    avatar_mime = Column(String, nullable=True)
    avatar_filename = Column(String, nullable=True)
    bio = Column(Text, nullable=True)

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


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    buyer_id = Column(Integer, ForeignKey("users.id"))
    seller_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    buyer_archived = Column(Boolean, default=False)
    seller_archived = Column(Boolean, default=False)
    buyer_deleted = Column(Boolean, default=False)
    seller_deleted = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)

    product = relationship("Product")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    room = relationship("ChatRoom")
    sender = relationship("User")
