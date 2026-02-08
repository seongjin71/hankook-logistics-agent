"""
대시보드 관련 Pydantic 스키마
"""

from pydantic import BaseModel


class OrdersSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]  # "HIGH" (>70), "MEDIUM" (40~70), "LOW" (<40)


class InventorySummary(BaseModel):
    low_stock_count: int  # 안전재고 이하 SKU 수
    total_skus: int


class VehiclesSummary(BaseModel):
    by_status: dict[str, int]


class VehicleDetail(BaseModel):
    vehicle_code: str
    vehicle_type: str
    status: str
    destination: str | None
    fuel_level: float
    speed_kmh: float


class LowStockDetail(BaseModel):
    warehouse_code: str
    product_code: str
    product_name: str
    available_qty: int
    safety_stock: int


class SimulationStatus(BaseModel):
    speed: int
    is_running: bool


class DashboardOverview(BaseModel):
    orders_summary: OrdersSummary
    inventory_summary: InventorySummary
    vehicles_summary: VehiclesSummary
    simulation: SimulationStatus
    vehicles: list[VehicleDetail] = []
    low_stock_details: list[LowStockDetail] = []
    recent_anomalies: int = 0
