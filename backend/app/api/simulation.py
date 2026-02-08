"""
시뮬레이션 API — 이상 시나리오 트리거, 속도 변경, 데모 시나리오, 리셋
"""

import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal, engine, Base
from app.schemas.simulation import (
    TriggerAnomalyRequest, TriggerAnomalyResponse,
    SpeedRequest, SpeedResponse,
)
from app.simulator.simulation_manager import simulation_manager
from app.simulator.demo_scenario import demo_scenario

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


@router.post("/trigger-anomaly", response_model=TriggerAnomalyResponse)
async def trigger_anomaly(req: TriggerAnomalyRequest, db: Session = Depends(get_db)):
    """이상 시나리오를 수동으로 트리거한다."""
    injector = simulation_manager.anomaly_injector

    loop = asyncio.get_event_loop()

    if req.scenario == "ORDER_SURGE":
        result = await loop.run_in_executor(None, injector.inject_order_surge, db)
    elif req.scenario == "VEHICLE_BREAKDOWN":
        vehicle_id = req.params.get("vehicle_id")
        result = await loop.run_in_executor(
            None, lambda: injector.inject_vehicle_breakdown(db, vehicle_id=vehicle_id)
        )
    elif req.scenario == "STOCK_SHORTAGE":
        warehouse_id = req.params.get("warehouse_id")
        product_id = req.params.get("product_id")
        result = await loop.run_in_executor(
            None, lambda: injector.inject_stock_shortage(db, warehouse_id=warehouse_id, product_id=product_id)
        )
    elif req.scenario == "SLA_RISK":
        result = await loop.run_in_executor(None, injector.inject_sla_risk, db)
    elif req.scenario == "DOCK_CONGESTION":
        warehouse_id = req.params.get("warehouse_id")
        result = await loop.run_in_executor(
            None, lambda: injector.inject_dock_congestion(db, warehouse_id=warehouse_id)
        )
    else:
        return TriggerAnomalyResponse(
            message="알 수 없는 시나리오",
            scenario=req.scenario,
        )

    # AsyncEventBus에도 이벤트 발행 (Monitor Agent가 감지하도록)
    if simulation_manager.async_event_bus:
        await simulation_manager.async_event_bus.publish("anomaly.detected", {
            "type": req.scenario,
            "severity": "CRITICAL",
            "source": "manual_trigger",
            "detail": result,
        })

    # WebSocket 브로드캐스트
    from app.api.websocket import broadcast_event
    await broadcast_event("anomaly_detected", {
        "scenario": req.scenario,
        "detail": result,
    })

    return TriggerAnomalyResponse(
        message=f"{req.scenario} 시나리오 주입 완료",
        scenario=req.scenario,
        detail=result,
    )


@router.put("/speed", response_model=SpeedResponse)
def set_speed(req: SpeedRequest):
    """시뮬레이션 속도 변경 (1x, 5x, 10x)"""
    simulation_manager.speed = req.speed
    return SpeedResponse(
        message=f"시뮬레이션 속도가 {req.speed}x로 변경되었습니다",
        speed=req.speed,
    )


# ── Demo Scenario APIs ──

@router.post("/start-demo")
async def start_demo():
    """15분 데모 시나리오를 시작한다."""
    result = await demo_scenario.start()
    return result


@router.get("/demo-status")
def get_demo_status():
    """현재 데모 진행 상태를 반환한다."""
    return demo_scenario.status


@router.post("/stop-demo")
async def stop_demo():
    """실행 중인 데모를 중지한다."""
    result = await demo_scenario.stop()
    return result


@router.post("/reset")
async def reset_data():
    """전체 데이터를 초기 상태로 리셋한다 (seed data 재실행)."""
    # Stop demo if running
    if demo_scenario.is_running:
        await demo_scenario.stop()

    # Stop simulation
    await simulation_manager.stop()

    # Reset database
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _reset_database)

    # Reset order sequence counter
    simulation_manager.order_simulator.reset_sequence()

    # Restart simulation
    await simulation_manager.start()

    logger.info("[Reset] 데이터 초기화 완료")

    from app.api.websocket import broadcast_event
    await broadcast_event("system_reset", {"message": "System reset complete"})

    return {"status": "ok", "message": "데이터가 초기 상태로 리셋되었습니다"}


def _reset_database():
    """DB 리셋 (블로킹)"""
    from app.models import (
        Order, OrderItem, Shipment, AgentEvent, PriorityHistory,
        Inventory, Vehicle,
    )
    from app.models.vehicle import VehicleStatus

    db = SessionLocal()
    try:
        # Clear transactional data
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(Shipment).delete()
        db.query(AgentEvent).delete()
        db.query(PriorityHistory).delete()
        db.commit()

        # Reset vehicle statuses
        db.query(Vehicle).update({
            Vehicle.status: VehicleStatus.AVAILABLE,
            Vehicle.current_speed_kmh: 0,
        })
        db.commit()

        # Reset inventory to safety stock levels
        inventories = db.query(Inventory).all()
        for inv in inventories:
            inv.available_qty = inv.safety_stock + 50
            inv.reserved_qty = 0
        db.commit()

        logger.info("[Reset] DB 리셋 완료")
    except Exception as e:
        db.rollback()
        logger.error(f"[Reset] DB 리셋 실패: {e}")
        raise
    finally:
        db.close()
