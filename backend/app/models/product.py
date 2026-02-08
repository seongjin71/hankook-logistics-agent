"""
products 테이블 — 한국타이어 제품(타이어 SKU) 정보
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Enum, DateTime

from app.database import Base


class ProductCategory(str, enum.Enum):
    PASSENGER = "PASSENGER"
    SUV = "SUV"
    TRUCK = "TRUCK"
    BUS = "BUS"


class PriorityGrade(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sku_code = Column(String(20), unique=True, nullable=False)  # 예: "HK-P-195-65R15-001"
    name = Column(String(100))  # 예: "Ventus Prime 4 195/65R15"
    category = Column(Enum(ProductCategory), nullable=False)
    tire_size = Column(String(20))  # 예: "195/65R15"
    weight_kg = Column(Float, nullable=False)
    priority_grade = Column(Enum(PriorityGrade), nullable=False)  # A가 최우선
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
