"""
shipments 테이블 — 출하/배송 정보
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey

from app.database import Base


class ShipmentStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    PICKING = "PICKING"
    PACKED = "PACKED"
    LOADING = "LOADING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_code = Column(String(20), unique=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    status = Column(Enum(ShipmentStatus), default=ShipmentStatus.PLANNED, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
