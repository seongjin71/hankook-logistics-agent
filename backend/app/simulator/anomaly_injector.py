"""
이상 상황 주입기 — 다양한 이상 시나리오를 시뮬레이션에 주입한다.

시나리오:
  1. ORDER_SURGE: 주문 폭주 (20~30건 동시 생성)
  2. VEHICLE_BREAKDOWN: 차량 고장
  3. STOCK_SHORTAGE: 재고 부족 (안전재고 이하)
  4. SLA_RISK: VIP 납기 위반 위험
  5. DOCK_CONGESTION: 도크 혼잡 (90% 이상 점유)
"""

import random
import uuid
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Vehicle, Inventory, Order, Warehouse, Customer, Product, AgentEvent,
)
from app.models.vehicle import VehicleStatus
from app.models.order import OrderStatus
from app.models.customer import CustomerGrade
from app.models.agent_event import AgentType, OODAPhase, EventSeverity
from app.simulator.event_bus import EventBus
from app.simulator.order_simulator import OrderSimulator

logger = logging.getLogger(__name__)


class AnomalyInjector:
    """이상 상황 주입기"""

    def __init__(self, event_bus: EventBus, order_simulator: OrderSimulator):
        self.event_bus = event_bus
        self.order_simulator = order_simulator

    def _log_agent_event(self, db: Session, event_type: str, severity: EventSeverity,
                         title: str, description: str, payload: dict) -> str:
        """에이전트 이벤트 로그 기록 후 event_id 반환"""
        event_id = str(uuid.uuid4())
        event = AgentEvent(
            event_id=event_id,
            agent_type=AgentType.MONITOR,
            ooda_phase=OODAPhase.OBSERVE,
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            payload=payload,
        )
        db.add(event)
        return event_id

    def inject_order_surge(self, db: Session | None = None) -> dict:
        """
        주문 폭주 — 짧은 시간에 20~30건 동시 생성
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            count = random.randint(20, 30)
            created_orders = []

            for _ in range(count):
                order = self.order_simulator.generate_order(db)
                if order:
                    created_orders.append(order.order_code)

            # 에이전트 이벤트 기록
            self._log_agent_event(
                db,
                event_type="ORDER_SURGE",
                severity=EventSeverity.CRITICAL,
                title=f"주문 폭주 감지: {count}건 동시 접수",
                description=f"짧은 시간 내에 {count}건의 주문이 동시에 접수되었습니다. "
                            f"창고 처리 용량 초과 가능성이 있습니다.",
                payload={"order_count": count, "order_codes": created_orders},
            )

            db.commit()

            # 이벤트 버스 발행
            self.event_bus.publish("anomaly.detected", {
                "type": "ORDER_SURGE",
                "severity": "CRITICAL",
                "order_count": count,
            })

            logger.warning(f"[이상주입] ORDER_SURGE: {count}건 주문 폭주")
            return {"scenario": "ORDER_SURGE", "orders_created": count,
                    "order_codes": created_orders}

        except Exception as e:
            db.rollback()
            logger.error(f"ORDER_SURGE 주입 실패: {e}")
            raise
        finally:
            if own_session:
                db.close()

    def inject_vehicle_breakdown(self, db: Session | None = None,
                                 vehicle_id: int | None = None) -> dict:
        """
        차량 고장 — 특정 차량 상태를 BREAKDOWN으로 변경
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            if vehicle_id:
                vehicle = db.query(Vehicle).get(vehicle_id)
            else:
                # 랜덤으로 가용 차량 선택
                available = db.query(Vehicle).filter(
                    Vehicle.status.in_([VehicleStatus.AVAILABLE, VehicleStatus.IN_TRANSIT])
                ).all()
                if not available:
                    return {"scenario": "VEHICLE_BREAKDOWN", "message": "가용 차량 없음"}
                vehicle = random.choice(available)

            if not vehicle:
                return {"scenario": "VEHICLE_BREAKDOWN", "message": "차량을 찾을 수 없음"}

            old_status = vehicle.status.value
            vehicle.status = VehicleStatus.BREAKDOWN
            vehicle.current_speed_kmh = 0
            vehicle.updated_at = datetime.now(timezone.utc)

            self._log_agent_event(
                db,
                event_type="VEHICLE_BREAKDOWN",
                severity=EventSeverity.CRITICAL,
                title=f"차량 고장: {vehicle.vehicle_code}",
                description=f"차량 {vehicle.vehicle_code} ({vehicle.vehicle_type.value})이 "
                            f"고장 발생. 이전 상태: {old_status}",
                payload={
                    "vehicle_code": vehicle.vehicle_code,
                    "vehicle_type": vehicle.vehicle_type.value,
                    "previous_status": old_status,
                    "location": {"lat": vehicle.current_lat, "lng": vehicle.current_lng},
                },
            )

            db.commit()

            self.event_bus.publish("anomaly.detected", {
                "type": "VEHICLE_BREAKDOWN",
                "severity": "CRITICAL",
                "vehicle_code": vehicle.vehicle_code,
            })

            logger.warning(f"[이상주입] VEHICLE_BREAKDOWN: {vehicle.vehicle_code}")
            return {"scenario": "VEHICLE_BREAKDOWN",
                    "vehicle_code": vehicle.vehicle_code,
                    "previous_status": old_status}

        except Exception as e:
            db.rollback()
            logger.error(f"VEHICLE_BREAKDOWN 주입 실패: {e}")
            raise
        finally:
            if own_session:
                db.close()

    def inject_stock_shortage(self, db: Session | None = None,
                              warehouse_id: int | None = None,
                              product_id: int | None = None) -> dict:
        """
        재고 부족 — 특정 재고를 안전재고 이하로 강제 설정
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            query = db.query(Inventory).filter(Inventory.available_qty > 0)
            if warehouse_id:
                query = query.filter(Inventory.warehouse_id == warehouse_id)
            if product_id:
                query = query.filter(Inventory.product_id == product_id)

            inventories = query.all()
            if not inventories:
                return {"scenario": "STOCK_SHORTAGE", "message": "대상 재고 없음"}

            # 랜덤 3~5개 SKU 선택
            targets = random.sample(inventories, min(random.randint(3, 5), len(inventories)))
            shortage_info = []

            for inv in targets:
                old_qty = inv.available_qty
                # 안전재고의 30~70% 수준으로 감소
                new_qty = max(0, int(inv.safety_stock * random.uniform(0.1, 0.5)))
                inv.available_qty = new_qty
                inv.updated_at = datetime.now(timezone.utc)

                product = db.query(Product).get(inv.product_id)
                warehouse = db.query(Warehouse).get(inv.warehouse_id)

                shortage_info.append({
                    "warehouse": warehouse.code if warehouse else str(inv.warehouse_id),
                    "product_sku": product.sku_code if product else str(inv.product_id),
                    "old_qty": old_qty,
                    "new_qty": new_qty,
                    "safety_stock": inv.safety_stock,
                })

            self._log_agent_event(
                db,
                event_type="STOCK_SHORTAGE",
                severity=EventSeverity.WARNING,
                title=f"재고 부족 감지: {len(targets)}개 SKU",
                description=f"{len(targets)}개 SKU의 재고가 안전재고 이하로 감소했습니다.",
                payload={"shortage_items": shortage_info},
            )

            db.commit()

            self.event_bus.publish("anomaly.detected", {
                "type": "STOCK_SHORTAGE",
                "severity": "WARNING",
                "affected_skus": len(targets),
            })

            logger.warning(f"[이상주입] STOCK_SHORTAGE: {len(targets)}개 SKU")
            return {"scenario": "STOCK_SHORTAGE", "affected_items": shortage_info}

        except Exception as e:
            db.rollback()
            logger.error(f"STOCK_SHORTAGE 주입 실패: {e}")
            raise
        finally:
            if own_session:
                db.close()

    def inject_sla_risk(self, db: Session | None = None) -> dict:
        """
        SLA 위반 위험 — VIP 주문의 예상 배송시간을 SLA 초과로 설정
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            # RECEIVED 또는 PICKING 상태의 VIP 주문 찾기
            vip_orders = (
                db.query(Order)
                .join(Customer, Order.customer_id == Customer.id)
                .filter(
                    Customer.grade == CustomerGrade.VIP,
                    Order.status.in_([OrderStatus.RECEIVED, OrderStatus.PICKING]),
                )
                .all()
            )

            if not vip_orders:
                # VIP 주문이 없으면 새로 만들기
                logger.info("VIP 주문 없음 — 주문 생성 후 SLA 위험 주입")
                order = self.order_simulator.generate_order(db)
                if order:
                    vip_orders = [order]
                else:
                    return {"scenario": "SLA_RISK", "message": "VIP 주문 생성 실패"}

            # 1~3개 주문 선택
            targets = random.sample(vip_orders, min(random.randint(1, 3), len(vip_orders)))
            risk_info = []

            for order in targets:
                customer = db.query(Customer).get(order.customer_id)
                # 예상 배송 시간을 납기 이후로 설정
                delay_hours = random.uniform(2, 8)
                order.estimated_delivery_at = order.requested_delivery_at + timedelta(hours=delay_hours)
                order.updated_at = datetime.now(timezone.utc)

                risk_info.append({
                    "order_code": order.order_code,
                    "customer": customer.name if customer else "Unknown",
                    "customer_grade": customer.grade.value if customer else "Unknown",
                    "requested_delivery": order.requested_delivery_at.isoformat(),
                    "estimated_delivery": order.estimated_delivery_at.isoformat(),
                    "delay_hours": round(delay_hours, 1),
                })

            self._log_agent_event(
                db,
                event_type="SLA_RISK",
                severity=EventSeverity.CRITICAL,
                title=f"SLA 위반 위험: {len(targets)}건 주문",
                description=f"VIP 고객 {len(targets)}건의 주문이 납기를 초과할 위험이 있습니다.",
                payload={"risk_orders": risk_info},
            )

            db.commit()

            self.event_bus.publish("anomaly.detected", {
                "type": "SLA_RISK",
                "severity": "CRITICAL",
                "affected_orders": len(targets),
            })

            logger.warning(f"[이상주입] SLA_RISK: {len(targets)}건 VIP 주문")
            return {"scenario": "SLA_RISK", "affected_orders": risk_info}

        except Exception as e:
            db.rollback()
            logger.error(f"SLA_RISK 주입 실패: {e}")
            raise
        finally:
            if own_session:
                db.close()

    def inject_dock_congestion(self, db: Session | None = None,
                               warehouse_id: int | None = None) -> dict:
        """
        도크 혼잡 — 해당 창고 도크 점유율을 90% 이상으로 설정
        - 실제 도크 점유 테이블이 없으므로, LOADING 상태 차량 수를 늘려 표현한다.
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            if warehouse_id:
                warehouse = db.query(Warehouse).get(warehouse_id)
            else:
                warehouses = db.query(Warehouse).all()
                if not warehouses:
                    return {"scenario": "DOCK_CONGESTION", "message": "창고 없음"}
                warehouse = random.choice(warehouses)

            if not warehouse:
                return {"scenario": "DOCK_CONGESTION", "message": "창고를 찾을 수 없음"}

            # 해당 창고의 가용 차량을 LOADING 상태로 변경
            vehicles = db.query(Vehicle).filter(
                Vehicle.warehouse_id == warehouse.id,
                Vehicle.status == VehicleStatus.AVAILABLE,
            ).all()

            # 도크 수의 90% 이상 차량을 LOADING으로
            target_count = max(1, int(warehouse.dock_count * 0.9))
            loading_vehicles = vehicles[:min(target_count, len(vehicles))]

            for v in loading_vehicles:
                v.status = VehicleStatus.LOADING
                v.updated_at = datetime.now(timezone.utc)

            congestion_pct = (len(loading_vehicles) / warehouse.dock_count * 100
                              if warehouse.dock_count > 0 else 0)

            self._log_agent_event(
                db,
                event_type="DOCK_CONGESTION",
                severity=EventSeverity.WARNING,
                title=f"도크 혼잡: {warehouse.name} ({congestion_pct:.0f}%)",
                description=f"{warehouse.name}의 도크 점유율이 {congestion_pct:.0f}%에 도달했습니다. "
                            f"총 {warehouse.dock_count}개 도크 중 {len(loading_vehicles)}개 사용 중.",
                payload={
                    "warehouse_code": warehouse.code,
                    "warehouse_name": warehouse.name,
                    "dock_count": warehouse.dock_count,
                    "occupied": len(loading_vehicles),
                    "congestion_pct": round(congestion_pct, 1),
                },
            )

            db.commit()

            self.event_bus.publish("anomaly.detected", {
                "type": "DOCK_CONGESTION",
                "severity": "WARNING",
                "warehouse": warehouse.code,
                "congestion_pct": round(congestion_pct, 1),
            })

            logger.warning(f"[이상주입] DOCK_CONGESTION: {warehouse.name} ({congestion_pct:.0f}%)")
            return {
                "scenario": "DOCK_CONGESTION",
                "warehouse": warehouse.code,
                "dock_count": warehouse.dock_count,
                "occupied": len(loading_vehicles),
                "congestion_pct": round(congestion_pct, 1),
            }

        except Exception as e:
            db.rollback()
            logger.error(f"DOCK_CONGESTION 주입 실패: {e}")
            raise
        finally:
            if own_session:
                db.close()
