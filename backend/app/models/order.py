"""
orders / order_items 테이블 — 출하 주문 및 상세 품목
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PICKING = "PICKING"
    PACKED = "PACKED"
    LOADING = "LOADING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_code = Column(String(20), unique=True, nullable=False)  # "ORD-20260206-00001"
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.RECEIVED, nullable=False)
    priority_score = Column(Float, nullable=False, default=0.0)  # 현재 우선순위 (0~100)
    original_priority = Column(Float, nullable=False, default=0.0)  # 최초 산정 우선순위
    total_weight_kg = Column(Float, nullable=False, default=0.0)
    requested_delivery_at = Column(DateTime, nullable=False)  # 요청 납기
    estimated_delivery_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items = relationship("OrderItem", back_populates="order", lazy="selectin")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=False)  # quantity × product.weight_kg

    order = relationship("Order", back_populates="items")
