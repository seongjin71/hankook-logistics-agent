"""
StateSnapshot — Monitor Agent가 유지하는 인메모리 시스템 상태.
이벤트를 수신할 때마다 갱신되며, 이상 감지 규칙의 입력 데이터가 된다.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class OrderRateWindow:
    """이동 윈도우 기반 주문 유입률 추적"""
    # 최근 주문 타임스탬프 (이동 윈도우)
    timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))

    def record(self, ts: datetime | None = None):
        """주문 발생 기록"""
        self.timestamps.append(ts or datetime.now(timezone.utc))

    def count_in_minutes(self, minutes: int) -> int:
        """최근 N분간 주문 수"""
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - (minutes * 60)
        return sum(1 for ts in self.timestamps if ts.timestamp() > cutoff)

    @property
    def rate_10min(self) -> int:
        """최근 10분간 주문 수"""
        return self.count_in_minutes(10)

    @property
    def rate_60min_avg(self) -> float:
        """최근 1시간 평균 10분당 주문 수"""
        total_60 = self.count_in_minutes(60)
        return total_60 / 6.0  # 6개의 10분 구간


@dataclass
class StateSnapshot:
    """
    시스템 전체 상태 스냅샷.
    Monitor Agent가 이벤트를 수신할 때마다 갱신한다.
    """

    # 주문 유입률
    order_rate: OrderRateWindow = field(default_factory=OrderRateWindow)

    # 안전재고 이하 항목: {(warehouse_id, product_id): available_qty}
    low_stock_items: dict[tuple[int, int], int] = field(default_factory=dict)

    # 차량 상태: {vehicle_id: {"status": ..., "code": ..., ...}}
    vehicle_statuses: dict[int, dict] = field(default_factory=dict)

    # 창고별 도크 점유율: {warehouse_id: ratio (0.0~1.0)}
    dock_occupancy: dict[int, float] = field(default_factory=dict)

    # 미처리 주문 수
    pending_orders: int = 0

    # SLA 위반 위험 주문: {order_id: {"order_code": ..., "remaining_ratio": ..., ...}}
    sla_at_risk_orders: dict[int, dict] = field(default_factory=dict)

    # 최근 감지된 이상 기록 (cooldown 용): {rule_id: last_detected_time}
    last_detected: dict[str, datetime] = field(default_factory=dict)

    def update_from_db(self, db_data: dict):
        """DB에서 가져온 데이터로 상태 일괄 갱신 (초기화/주기적 동기화)"""
        if "low_stock_items" in db_data:
            self.low_stock_items = db_data["low_stock_items"]
        if "vehicle_statuses" in db_data:
            self.vehicle_statuses = db_data["vehicle_statuses"]
        if "dock_occupancy" in db_data:
            self.dock_occupancy = db_data["dock_occupancy"]
        if "pending_orders" in db_data:
            self.pending_orders = db_data["pending_orders"]
        if "sla_at_risk_orders" in db_data:
            self.sla_at_risk_orders = db_data["sla_at_risk_orders"]
