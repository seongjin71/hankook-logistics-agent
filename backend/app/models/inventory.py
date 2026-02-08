"""
inventory 테이블 — 창고별 SKU 재고 현황
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, UniqueConstraint

from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    available_qty = Column(Integer, nullable=False, default=0)  # 가용 재고
    reserved_qty = Column(Integer, nullable=False, default=0)  # 예약(피킹 중) 재고
    safety_stock = Column(Integer, nullable=False, default=50)  # 안전 재고 수준
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", name="uq_warehouse_product"),
    )
