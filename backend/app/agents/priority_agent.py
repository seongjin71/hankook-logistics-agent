"""
Priority Agent — OODA Decide 단계.
전체 미처리 주문의 우선순위를 다요소 스코어링 모델로 재계산한다.

스코어링 가중치:
  - 고객 등급: 25% (VIP:100, STANDARD:60, ECONOMY:30)
  - 납기 긴급도: 30% (max(0, 1 - 남은시간/SLA시간) × 100)
  - 제품 등급: 15% (A:100, B:60, C:30)
  - 재고 가용성: 15% (충분:100, 부분부족:50, 없음:0)
  - 이상상황 영향: 15% (affected_orders에 포함 시 +30)
"""

import time
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Order, Customer, Product, Inventory, PriorityHistory
from app.models.order import OrderItem, OrderStatus
from app.models.customer import CustomerGrade
from app.models.product import PriorityGrade
from app.models.agent_event import AgentType, OODAPhase, EventSeverity
from app.agents.event_logger import AgentEventLogger

logger = logging.getLogger(__name__)

# 가중치
W_CUSTOMER = 0.25
W_URGENCY = 0.30
W_PRODUCT = 0.15
W_INVENTORY = 0.15
W_ANOMALY = 0.15

# 고객 등급 점수
CUSTOMER_SCORES = {
    CustomerGrade.VIP: 100,
    CustomerGrade.STANDARD: 60,
    CustomerGrade.ECONOMY: 30,
}

# 제품 등급 점수
PRODUCT_SCORES = {
    PriorityGrade.A: 100,
    PriorityGrade.B: 60,
    PriorityGrade.C: 30,
}


class PriorityAgent:
    """Priority Agent — 우선순위 재계산 (OODA: Decide)"""

    def __init__(self):
        self.event_logger = AgentEventLogger()

    async def recalculate(self, analysis: dict, parent_event_id: str | None = None) -> dict:
        """
        Anomaly Agent 분석 결과를 받아 전체 미처리 주문의 우선순위를 재계산한다.
        Returns: 재계산 결과 dict
        """
        start = time.monotonic()
        event_type = analysis.get("event_type", "UNKNOWN")

        # affected_order 코드 리스트 추출
        affected_codes = set()
        for o in analysis.get("affected_orders", []):
            if isinstance(o, dict):
                affected_codes.add(o.get("order_code", ""))
            elif isinstance(o, str):
                affected_codes.add(o)

        logger.info(f"[Priority] 미처리 주문 우선순위 재계산 시작 (영향 주문: {len(affected_codes)}건)")

        # 블로킹 DB 작업
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._do_recalculate, affected_codes, parent_event_id
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        # agent_events에 기록
        await self.event_logger.log_event(
            agent_type=AgentType.PRIORITY,
            ooda_phase=OODAPhase.DECIDE,
            event_type=event_type,
            severity=EventSeverity.INFO,
            title=f"우선순위 재계산 완료: {result['changed_count']}건 변경",
            description=(
                f"미처리 주문 {result['total_orders']}건 중 "
                f"{result['changed_count']}건의 우선순위가 변경되었습니다. "
                f"상향: {result['upgraded_count']}건, 하향: {result['downgraded_count']}건."
            ),
            payload=result,
            parent_event_id=parent_event_id,
            duration_ms=duration_ms,
        )

        logger.info(
            f"[Priority] 재계산 완료: {result['total_orders']}건 중 {result['changed_count']}건 변경 "
            f"(상향 {result['upgraded_count']}건, 하향 {result['downgraded_count']}건, {duration_ms}ms)"
        )

        # WebSocket 브로드캐스트
        from app.api.websocket import broadcast_event
        await broadcast_event("agent_event", {
            "agent_type": "PRIORITY",
            "ooda_phase": "DECIDE",
            "event_type": event_type,
            "title": f"우선순위 재계산 완료: {result['changed_count']}건 변경",
        })

        return result

    def _do_recalculate(self, affected_codes: set[str], parent_event_id: str | None) -> dict:
        """블로킹 DB 우선순위 재계산"""
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # 미처리 주문 전체 조회
            orders = (
                db.query(Order)
                .filter(Order.status.in_([
                    OrderStatus.RECEIVED, OrderStatus.PICKING, OrderStatus.PACKED
                ]))
                .all()
            )

            changes = []
            upgraded = 0
            downgraded = 0

            for order in orders:
                customer = db.query(Customer).get(order.customer_id)
                if not customer:
                    continue

                # 주문 아이템의 제품 등급 조회
                items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                product_grades = []
                inventory_ok = True
                inventory_partial = False

                for item in items:
                    product = db.query(Product).get(item.product_id)
                    if product:
                        product_grades.append(product.priority_grade)

                    # 재고 가용성 체크
                    inv = (
                        db.query(Inventory)
                        .filter(
                            Inventory.warehouse_id == order.warehouse_id,
                            Inventory.product_id == item.product_id,
                        )
                        .first()
                    )
                    if inv:
                        if inv.available_qty < item.quantity:
                            if inv.available_qty == 0:
                                inventory_ok = False
                            else:
                                inventory_partial = True

                # 1. 고객 등급 점수 (25%)
                customer_score = CUSTOMER_SCORES.get(customer.grade, 30)

                # 2. 납기 긴급도 점수 (30%)
                remaining_hours = (order.requested_delivery_at - now).total_seconds() / 3600
                sla_hours = customer.sla_hours
                if sla_hours > 0:
                    urgency_score = max(0, min(100, (1 - remaining_hours / sla_hours) * 100))
                else:
                    urgency_score = 0

                # 3. 제품 등급 점수 (15%)
                if product_grades:
                    best_grade = min(product_grades, key=lambda g: ["A", "B", "C"].index(g.value))
                    product_score = PRODUCT_SCORES.get(best_grade, 30)
                else:
                    product_score = 30

                # 4. 재고 가용성 점수 (15%)
                if inventory_ok and not inventory_partial:
                    inventory_score = 100
                elif inventory_partial:
                    inventory_score = 50
                else:
                    inventory_score = 0

                # 5. 이상상황 영향 점수 (15%)
                anomaly_score = 30 if order.order_code in affected_codes else 0

                # 총점 계산
                new_score = round(
                    customer_score * W_CUSTOMER +
                    urgency_score * W_URGENCY +
                    product_score * W_PRODUCT +
                    inventory_score * W_INVENTORY +
                    anomaly_score * W_ANOMALY,
                    2,
                )
                new_score = min(100, max(0, new_score))

                # 변경 발생 시 기록
                old_score = order.priority_score
                if abs(new_score - old_score) >= 0.5:
                    order.priority_score = new_score
                    order.updated_at = now

                    # priority_history 기록
                    direction = "상향" if new_score > old_score else "하향"
                    db.add(PriorityHistory(
                        order_id=order.id,
                        previous_score=old_score,
                        new_score=new_score,
                        reason=f"이상상황 분석에 따른 우선순위 {direction} 조정",
                        agent_event_id=parent_event_id,
                    ))

                    if new_score > old_score:
                        upgraded += 1
                    else:
                        downgraded += 1

                    changes.append({
                        "order_code": order.order_code,
                        "old_score": old_score,
                        "new_score": new_score,
                        "direction": direction,
                    })

            db.commit()

            return {
                "total_orders": len(orders),
                "changed_count": len(changes),
                "upgraded_count": upgraded,
                "downgraded_count": downgraded,
                "changes": changes[:20],  # 상위 20건만
            }

        except Exception as e:
            db.rollback()
            logger.error(f"우선순위 재계산 실패: {e}")
            raise
        finally:
            db.close()
