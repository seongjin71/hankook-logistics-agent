"""
vehicles 테이블 — 배송 차량 정보 (15대)
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Enum, DateTime, ForeignKey

from app.database import Base


class VehicleType(str, enum.Enum):
    T5 = "5T"
    T11 = "11T"
    T25 = "25T"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_TRANSIT = "IN_TRANSIT"
    LOADING = "LOADING"
    MAINTENANCE = "MAINTENANCE"
    BREAKDOWN = "BREAKDOWN"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_code = Column(String(20), unique=True, nullable=False)  # "VH-001" ~ "VH-015"
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    max_capacity_kg = Column(Float, nullable=False)
    status = Column(Enum(VehicleStatus), default=VehicleStatus.AVAILABLE, nullable=False)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    current_speed_kmh = Column(Float, default=0)
    fuel_level_pct = Column(Float, default=100.0)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
