import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from order_service.db import Base


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_phone = Column(String(15), nullable=False)
    items = Column(JSON, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    gst = Column(Numeric(10, 2), nullable=False)
    delivery_fee = Column(Numeric(10, 2), default=0.0)
    total = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(10), nullable=False)  # 'COD' or 'UPI'
    payment_status = Column(String(20), default="PENDING")
    delivery_address = Column(JSON, nullable=False)
    status = Column(String(30), default="CREATED")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CartItemDB(Base):
    __tablename__ = "cart_items"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), nullable=False)
    product_id = Column(String(50), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Numeric(10, 2), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
