"""
customers 테이블 — 고객사 정보
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Enum, DateTime

from app.database import Base


class CustomerGrade(str, enum.Enum):
    VIP = "VIP"
    STANDARD = "STANDARD"
    ECONOMY = "ECONOMY"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # 예: "현대자동차"
    customer_code = Column(String(20), unique=True, nullable=False)
    region = Column(String(50))  # 예: "서울", "부산"
    grade = Column(Enum(CustomerGrade), nullable=False)
    sla_hours = Column(Integer, nullable=False)  # VIP: 12h, STANDARD: 24h, ECONOMY: 48h
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
