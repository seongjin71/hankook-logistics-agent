"""
대시보드 API — 전체 현황 요약 데이터 제공
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Order, Inventory, Vehicle, Product, Warehouse, AgentEvent
from app.models.order import OrderStatus
from app.models.vehicle import VehicleStatus
from app.schemas.dashboard import (
    DashboardOverview, OrdersSummary, InventorySummary,
    VehiclesSummary, VehicleDetail, LowStockDetail, SimulationStatus,
)
from app.simulator.simulation_manager import simulation_manager

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db)):
    """대시보드 전체 현황 반환"""

    # --- 주문 요약 ---
    total_orders = db.query(func.count(Order.id)).scalar() or 0

    # 상태별 집계
    status_counts = (
        db.query(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .all()
    )
    by_status = {status.value if hasattr(status, 'value') else str(status): count
                 for status, count in status_counts}

    # 우선순위 등급별 집계 (HIGH: >70, MEDIUM: 40~70, LOW: <40)
    high = db.query(func.count(Order.id)).filter(Order.priority_score > 70).scalar() or 0
    medium = db.query(func.count(Order.id)).filter(
        Order.priority_score >= 40, Order.priority_score <= 70
    ).scalar() or 0
    low = db.query(func.count(Order.id)).filter(Order.priority_score < 40).scalar() or 0
    by_priority = {"HIGH": high, "MEDIUM": medium, "LOW": low}

    orders_summary = OrdersSummary(
        total=total_orders,
        by_status=by_status,
        by_priority=by_priority,
    )

    # --- 재고 요약 ---
    total_skus = db.query(func.count(func.distinct(Inventory.product_id))).scalar() or 0
    low_stock_count = (
        db.query(func.count(Inventory.id))
        .filter(Inventory.available_qty <= Inventory.safety_stock)
        .scalar() or 0
    )

    inventory_summary = InventorySummary(
        low_stock_count=low_stock_count,
        total_skus=total_skus,
    )

    # --- 재고 부족 상세 ---
    low_stock_rows = (
        db.query(Inventory, Product.sku_code, Product.name, Warehouse.code)
        .join(Product, Product.id == Inventory.product_id)
        .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
        .filter(Inventory.available_qty <= Inventory.safety_stock)
        .order_by(Inventory.available_qty)
        .limit(10)
        .all()
    )
    low_stock_details = [
        LowStockDetail(
            warehouse_code=wh_code,
            product_code=sku_code,
            product_name=p_name,
            available_qty=inv.available_qty,
            safety_stock=inv.safety_stock,
        )
        for inv, sku_code, p_name, wh_code in low_stock_rows
    ]

    # --- 차량 요약 ---
    vehicle_counts = (
        db.query(Vehicle.status, func.count(Vehicle.id))
        .group_by(Vehicle.status)
        .all()
    )
    vehicle_by_status = {status.value if hasattr(status, 'value') else str(status): count
                         for status, count in vehicle_counts}

    vehicles_summary = VehiclesSummary(by_status=vehicle_by_status)

    # --- 차량 상세 ---
    all_vehicles = db.query(Vehicle).all()
    vehicle_details = [
        VehicleDetail(
            vehicle_code=v.vehicle_code,
            vehicle_type=v.vehicle_type.value if hasattr(v.vehicle_type, 'value') else str(v.vehicle_type),
            status=v.status.value if hasattr(v.status, 'value') else str(v.status),
            destination=None,
            fuel_level=v.fuel_level_pct,
            speed_kmh=v.current_speed_kmh,
        )
        for v in all_vehicles
    ]

    # --- 최근 이상 감지 수 (최근 1시간) ---
    one_hour_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    recent_anomalies = (
        db.query(func.count(AgentEvent.id))
        .filter(
            AgentEvent.ooda_phase == "OBSERVE",
            AgentEvent.created_at >= one_hour_ago,
        )
        .scalar() or 0
    )

    # --- 시뮬레이션 상태 ---
    sim_status = SimulationStatus(
        speed=simulation_manager.speed,
        is_running=simulation_manager.is_running,
    )

    return DashboardOverview(
        orders_summary=orders_summary,
        inventory_summary=inventory_summary,
        vehicles_summary=vehicles_summary,
        simulation=sim_status,
        vehicles=vehicle_details,
        low_stock_details=low_stock_details,
        recent_anomalies=recent_anomalies,
    )
