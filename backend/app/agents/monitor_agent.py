"""
Monitor Agent — OODA Observe 단계 담당.
모든 데이터 이벤트를 구독하고 StateSnapshot을 갱신하며,
Rule-based 이상 감지를 수행한다.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.database import SessionLocal
from app.events.event_bus import AsyncEventBus
from app.agents.state_snapshot import StateSnapshot
from app.agents.event_logger import AgentEventLogger
from app.agents.rules import ALL_RULES, AnomalyEvent
from app.models import (
    Order, Customer, Inventory, Vehicle, Warehouse,
)
from app.models.order import OrderStatus
from app.models.vehicle import VehicleStatus
from app.models.agent_event import AgentType, OODAPhase

logger = logging.getLogger(__name__)

# 중복 감지 방지 쿨다운 (초)
COOLDOWN_SECONDS = 300  # 5분


class MonitorAgent:
    """
    OODA: Observe 단계.
    - 이벤트 구독 → StateSnapshot 갱신
    - Rule-based 이상 감지
    - 감지 시 agent_events 기록 + anomaly.detected 발행
    """

    def __init__(self, event_bus: AsyncEventBus):
        self.event_bus = event_bus
        self.state = StateSnapshot()
        self.event_logger = AgentEventLogger()
        self._running = False
        self._sync_task: asyncio.Task | None = None

    async def start(self):
        """Monitor Agent 시작 — 이벤트 구독 등록 및 초기 상태 로드"""
        logger.info("Monitor Agent 시작")

        # 이벤트 구독 등록
        await self.event_bus.subscribe("orders.created", self._on_order_created)
        await self.event_bus.subscribe("orders.status_changed", self._on_order_status_changed)
        await self.event_bus.subscribe("inventory.updated", self._on_inventory_updated)
        await self.event_bus.subscribe("vehicles.updated", self._on_vehicle_updated)
        await self.event_bus.subscribe("anomaly.detected", self._on_anomaly_detected)

        # DB에서 초기 상태 로드
        await self._sync_from_db()

        # 주기적 DB 동기화 태스크 시작
        self._running = True
        self._sync_task = asyncio.create_task(self._periodic_sync_loop())

        logger.info("Monitor Agent 준비 완료 — 이벤트 구독 활성화")

    async def stop(self):
        """Monitor Agent 중지"""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Monitor Agent 중지")

    # ── 이벤트 핸들러 ──────────────────────────────────────

    async def _on_order_created(self, topic: str, data: dict):
        """새 주문 생성 이벤트 처리"""
        self.state.order_rate.record()
        self.state.pending_orders += 1
        logger.debug(f"[Monitor] 주문 생성 감지: {data.get('order_code', 'N/A')}")

        # 이상 감지 규칙 실행
        await self._run_rules()

    async def _on_order_status_changed(self, topic: str, data: dict):
        """주문 상태 변경 이벤트 처리"""
        new_status = data.get("new_status", "")
        # 미처리 → 처리완료 시 pending 감소
        if new_status in ("PACKED", "LOADING", "SHIPPED", "DELIVERED"):
            self.state.pending_orders = max(0, self.state.pending_orders - 1)

        await self._run_rules()

    async def _on_inventory_updated(self, topic: str, data: dict):
        """재고 변동 이벤트 처리"""
        warehouse_id = data.get("warehouse_id")
        product_id = data.get("product_id")
        available_qty = data.get("available_qty")
        safety_stock = data.get("safety_stock")

        if warehouse_id and product_id and available_qty is not None and safety_stock is not None:
            key = (int(warehouse_id), int(product_id))
            if int(available_qty) <= int(safety_stock):
                self.state.low_stock_items[key] = int(available_qty)
            elif key in self.state.low_stock_items:
                del self.state.low_stock_items[key]

        await self._run_rules()

    async def _on_vehicle_updated(self, topic: str, data: dict):
        """차량 상태/위치 변경 이벤트 처리"""
        vehicle_code = data.get("vehicle_code", "")
        status = data.get("status", "")

        # vehicle_id가 없을 수 있으므로 code 기반으로 저장
        # DB 동기화에서 id 기반으로 갱신됨
        for vid, vinfo in self.state.vehicle_statuses.items():
            if vinfo.get("code") == vehicle_code:
                vinfo["status"] = status
                vinfo["lat"] = data.get("lat")
                vinfo["lng"] = data.get("lng")
                vinfo["speed_kmh"] = data.get("speed_kmh", 0)
                vinfo["fuel_pct"] = data.get("fuel_pct", 100)
                break

        await self._run_rules()

    async def _on_anomaly_detected(self, topic: str, data: dict):
        """외부에서 이상이 주입된 경우 — 상태 동기화만 수행"""
        anomaly_type = data.get("type", "")
        logger.debug(f"[Monitor] 외부 이상 감지 이벤트 수신: {anomaly_type}")
        # 다음 주기적 동기화에서 DB 상태가 반영됨
        # 즉시 동기화 트리거
        await self._sync_from_db()
        await self._run_rules()

    # ── 이상 감지 규칙 실행 ─────────────────────────────────

    async def _run_rules(self):
        """모든 이상 감지 규칙을 실행하고, 감지된 이상을 기록/발행한다."""
        now = datetime.now(timezone.utc)

        for rule in ALL_RULES:
            try:
                result: AnomalyEvent | None = rule.check(self.state)
                if result is None:
                    continue

                # 쿨다운 체크: 같은 rule_id가 5분 이내 감지되었으면 무시
                last = self.state.last_detected.get(rule.rule_id)
                if last and (now - last).total_seconds() < COOLDOWN_SECONDS:
                    continue

                # 쿨다운 기록 갱신
                self.state.last_detected[rule.rule_id] = now

                # agent_events 테이블에 기록
                agent_event = await self.event_logger.log_event(
                    agent_type=AgentType.MONITOR,
                    ooda_phase=OODAPhase.OBSERVE,
                    event_type=result.event_type,
                    severity=result.severity,
                    title=result.title,
                    description=result.description,
                    payload=result.payload,
                )

                # anomaly.detected 토픽에 발행
                await self.event_bus.publish("anomaly.detected", {
                    "type": result.event_type,
                    "severity": result.severity.value,
                    "title": result.title,
                    "description": result.description,
                    "event_id": agent_event.event_id,
                    "payload": result.payload,
                    "source": "monitor_agent",
                })

                logger.warning(
                    f"[Monitor] 이상 감지: {result.event_type} "
                    f"[{result.severity.value}] — {result.title}"
                )

            except Exception as e:
                logger.error(f"규칙 실행 에러 ({rule.rule_id}): {e}")

    # ── DB 동기화 ──────────────────────────────────────────

    async def _periodic_sync_loop(self):
        """주기적으로 DB에서 상태를 동기화한다 (15초 간격)."""
        while self._running:
            try:
                await asyncio.sleep(15)
                if self._running:
                    await self._sync_from_db()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"주기적 동기화 에러: {e}")
                await asyncio.sleep(5)

    async def _sync_from_db(self):
        """DB에서 현재 상태를 읽어 StateSnapshot을 갱신한다."""
        loop = asyncio.get_event_loop()
        try:
            db_data = await loop.run_in_executor(None, self._query_db_state)
            self.state.update_from_db(db_data)
            logger.debug(
                f"[Monitor] DB 동기화: pending={self.state.pending_orders}, "
                f"low_stock={len(self.state.low_stock_items)}, "
                f"sla_risk={len(self.state.sla_at_risk_orders)}"
            )
        except Exception as e:
            logger.error(f"DB 동기화 실패: {e}")

    def _query_db_state(self) -> dict:
        """블로킹 DB 쿼리 — run_in_executor에서 호출"""
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive로 통일 (SQLite 호환)
            result = {}

            # 미처리 주문 수
            result["pending_orders"] = (
                db.query(func.count(Order.id))
                .filter(Order.status.in_([OrderStatus.RECEIVED, OrderStatus.PICKING]))
                .scalar() or 0
            )

            # 안전재고 이하 항목
            low_items = (
                db.query(Inventory)
                .filter(Inventory.available_qty <= Inventory.safety_stock)
                .all()
            )
            result["low_stock_items"] = {
                (inv.warehouse_id, inv.product_id): inv.available_qty
                for inv in low_items
            }

            # 차량 상태
            vehicles = db.query(Vehicle).all()
            result["vehicle_statuses"] = {
                v.id: {
                    "code": v.vehicle_code,
                    "status": v.status.value if hasattr(v.status, 'value') else str(v.status),
                    "type": v.vehicle_type.value if hasattr(v.vehicle_type, 'value') else str(v.vehicle_type),
                    "lat": v.current_lat,
                    "lng": v.current_lng,
                    "speed_kmh": v.current_speed_kmh,
                    "fuel_pct": v.fuel_level_pct,
                    "warehouse_id": v.warehouse_id,
                }
                for v in vehicles
            }

            # 도크 점유율 — LOADING 차량 수 / 도크 수
            warehouses = db.query(Warehouse).all()
            dock_occ = {}
            for wh in warehouses:
                loading_count = (
                    db.query(func.count(Vehicle.id))
                    .filter(
                        Vehicle.warehouse_id == wh.id,
                        Vehicle.status == VehicleStatus.LOADING,
                    )
                    .scalar() or 0
                )
                dock_occ[wh.id] = loading_count / wh.dock_count if wh.dock_count > 0 else 0
            result["dock_occupancy"] = dock_occ

            # SLA 위반 위험 주문
            # 남은 시간이 SLA의 30% 미만이고 아직 초기 상태인 주문
            sla_risk_orders = {}
            early_orders = (
                db.query(Order, Customer)
                .join(Customer, Order.customer_id == Customer.id)
                .filter(Order.status.in_([OrderStatus.RECEIVED, OrderStatus.PICKING]))
                .all()
            )
            for order, customer in early_orders:
                remaining = (order.requested_delivery_at - now).total_seconds() / 3600
                sla_hours = customer.sla_hours
                if sla_hours > 0:
                    remaining_ratio = remaining / sla_hours
                    if remaining_ratio < 0.3:
                        sla_risk_orders[order.id] = {
                            "order_id": order.id,
                            "order_code": order.order_code,
                            "customer_name": customer.name,
                            "customer_grade": customer.grade.value,
                            "remaining_hours": round(remaining, 1),
                            "sla_hours": sla_hours,
                            "remaining_ratio": round(remaining_ratio, 3),
                        }

            result["sla_at_risk_orders"] = sla_risk_orders

            return result

        finally:
            db.close()
