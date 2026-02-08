"""
주문 시뮬레이터 — 랜덤 주문을 자동 생성한다.
- 고객, SKU, 수량을 랜덤으로 조합
- 우선순위 초기 스코어를 계산
- 재고를 reserved_qty로 이동
- EventBus에 orders.created 이벤트 발행
"""

import random
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Product, Customer, Warehouse, Inventory, Order, OrderItem
from app.models.customer import CustomerGrade
from app.models.product import PriorityGrade
from app.simulator.data_generator import DataGenerator
from app.simulator.event_bus import EventBus

logger = logging.getLogger(__name__)

# 고객 등급별 기본 가중치
GRADE_WEIGHT = {
    CustomerGrade.VIP: 40,
    CustomerGrade.STANDARD: 25,
    CustomerGrade.ECONOMY: 10,
}


class OrderSimulator:
    """주문 시뮬레이터"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._order_seq = self._init_seq_from_db()

    def _init_seq_from_db(self) -> int:
        """DB에서 오늘 날짜의 최대 주문 시퀀스를 조회하여 초기화"""
        try:
            db = SessionLocal()
            today_prefix = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-"
            last_order = (
                db.query(Order)
                .filter(Order.order_code.like(f"{today_prefix}%"))
                .order_by(Order.order_code.desc())
                .first()
            )
            db.close()
            if last_order:
                seq = int(last_order.order_code.split("-")[-1])
                logger.info(f"주문 시퀀스 초기화: {seq} (DB 기준)")
                return seq
        except Exception as e:
            logger.warning(f"주문 시퀀스 DB 조회 실패, 0에서 시작: {e}")
        return 0

    def reset_sequence(self):
        """시퀀스를 0으로 리셋 (데이터 초기화 후 호출)"""
        self._order_seq = 0

    def _next_order_code(self) -> str:
        """고유 주문 코드 생성"""
        self._order_seq += 1
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")
        return f"ORD-{date_str}-{self._order_seq:05d}"

    def calculate_priority(self, customer: Customer, products_in_order: list[Product],
                           requested_delivery_at: datetime) -> float:
        """
        우선순위 초기 스코어 계산:
          base_score = 고객등급 가중치 (VIP:40, STANDARD:25, ECONOMY:10)
          urgency = max(0, (sla_hours - 남은시간) / sla_hours) × 30
          product_weight = Grade A 포함 시 +15, B만 +5
          priority_score = base_score + urgency + product_weight + random(0~10)
        """
        # 기본 점수
        base_score = GRADE_WEIGHT.get(customer.grade, 10)

        # 긴급도 — 남은 시간 대비 SLA
        now = datetime.now(timezone.utc)
        remaining_hours = (requested_delivery_at - now).total_seconds() / 3600
        if customer.sla_hours > 0:
            urgency = max(0, (customer.sla_hours - remaining_hours) / customer.sla_hours) * 30
        else:
            urgency = 0

        # 제품 등급 가중치
        grades = {p.priority_grade for p in products_in_order}
        if PriorityGrade.A in grades:
            product_weight = 15
        elif PriorityGrade.B in grades:
            product_weight = 5
        else:
            product_weight = 0

        # 최종 점수 (0~100 범위로 클리핑)
        score = base_score + urgency + product_weight + random.uniform(0, 10)
        return round(min(100, max(0, score)), 2)

    def generate_order(self, db: Session | None = None) -> Order | None:
        """
        랜덤 주문 1건 생성
        - db 세션이 주어지지 않으면 새로 생성한다.
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            # 랜덤 고객 선택
            customers = db.query(Customer).all()
            if not customers:
                logger.warning("고객 데이터 없음 — 주문 생성 스킵")
                return None
            customer = random.choice(customers)

            # 랜덤 창고 선택
            warehouses = db.query(Warehouse).all()
            if not warehouses:
                logger.warning("창고 데이터 없음 — 주문 생성 스킵")
                return None
            warehouse = random.choice(warehouses)

            # 랜덤 SKU 1~5개 선택
            all_products = db.query(Product).all()
            if not all_products:
                logger.warning("제품 데이터 없음 — 주문 생성 스킵")
                return None
            num_items = random.randint(1, 5)
            selected_products = random.sample(all_products, min(num_items, len(all_products)))

            # 납기일 설정 — 현재 + SLA 시간 (± 약간의 변동)
            now = datetime.now(timezone.utc)
            delivery_variation = random.uniform(-2, 4)  # SLA 기준으로 약간의 변동
            requested_delivery_at = now + timedelta(hours=customer.sla_hours + delivery_variation)

            # 우선순위 계산
            priority_score = self.calculate_priority(customer, selected_products, requested_delivery_at)

            # 주문 생성
            order_code = self._next_order_code()
            order = Order(
                order_code=order_code,
                customer_id=customer.id,
                warehouse_id=warehouse.id,
                priority_score=priority_score,
                original_priority=priority_score,
                total_weight_kg=0,
                requested_delivery_at=requested_delivery_at,
            )
            db.add(order)
            db.flush()  # order.id 확보

            # 주문 아이템 생성 및 재고 예약
            total_weight = 0.0
            items_info = []
            for product in selected_products:
                qty = random.randint(4, 100)
                item_weight = qty * product.weight_kg
                total_weight += item_weight

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=qty,
                    weight_kg=item_weight,
                )
                db.add(order_item)

                # 재고 예약 (available → reserved)
                inv = db.query(Inventory).filter(
                    Inventory.warehouse_id == warehouse.id,
                    Inventory.product_id == product.id,
                ).first()
                if inv:
                    reserve = min(qty, inv.available_qty)
                    inv.available_qty -= reserve
                    inv.reserved_qty += reserve

                items_info.append({
                    "sku": product.sku_code,
                    "name": product.name,
                    "qty": qty,
                    "weight_kg": item_weight,
                })

            order.total_weight_kg = round(total_weight, 2)
            db.commit()

            # 이벤트 발행
            self.event_bus.publish("orders.created", {
                "order_code": order.order_code,
                "customer": customer.name,
                "customer_grade": customer.grade.value,
                "warehouse": warehouse.code,
                "priority_score": priority_score,
                "total_weight_kg": total_weight,
                "items_count": len(selected_products),
                "requested_delivery_at": requested_delivery_at.isoformat(),
            })

            logger.info(
                f"주문 생성: {order.order_code} | 고객: {customer.name} "
                f"| 우선순위: {priority_score} | 아이템: {len(selected_products)}개 "
                f"| 중량: {total_weight:.1f}kg"
            )
            return order

        except Exception as e:
            if own_session:
                db.rollback()
            logger.error(f"주문 생성 실패: {e}")
            raise
        finally:
            if own_session:
                db.close()
