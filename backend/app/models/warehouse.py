"""
warehouses 테이블 — 출하 창고 정보 (3곳)
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime

from app.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)  # "WH-DKJ", "WH-GMS", "WH-PYT"
    name = Column(String(50), nullable=False)  # "대전공장 물류센터" 등
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    dock_count = Column(Integer, nullable=False)  # 도크 수
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
