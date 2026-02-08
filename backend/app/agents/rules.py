"""
이상 감지 규칙 — Rule-based 방식으로 StateSnapshot을 분석한다.

각 규칙은 AnomalyRule 프로토콜을 구현:
  rule_id: str
  check(state) -> Optional[AnomalyEvent dict]
"""

import logging
from dataclasses import dataclass
from typing import Protocol

from app.agents.state_snapshot import StateSnapshot
from app.models.agent_event import EventSeverity

logger = logging.getLogger(__name__)


@dataclass
class AnomalyEvent:
    """감지된 이상 정보"""
    event_type: str
    severity: EventSeverity
    title: str
    description: str
    payload: dict


class AnomalyRule(Protocol):
    """이상 감지 규칙 프로토콜"""
    rule_id: str

    def check(self, state: StateSnapshot) -> AnomalyEvent | None: ...


class OrderSurgeRule:
    """
    주문 폭주 감지.
    order_rate_10min > order_rate_avg_10min × 2.0 이면 ORDER_SURGE.
    - 2x~3x: WARNING
    - 3x 이상: CRITICAL
    """

    rule_id = "order_surge"

    def check(self, state: StateSnapshot) -> AnomalyEvent | None:
        rate_10min = state.order_rate.rate_10min
        avg_10min = state.order_rate.rate_60min_avg

        # 최소 기준: 평균이 1건 이상, 현재 유입이 4건 이상이어야 의미 있음
        if avg_10min < 1 or rate_10min < 4:
            return None

        ratio = rate_10min / avg_10min
        if ratio < 2.0:
            return None

        severity = EventSeverity.CRITICAL if ratio >= 3.0 else EventSeverity.WARNING
        pct = int(ratio * 100)

        return AnomalyEvent(
            event_type="ORDER_SURGE",
            severity=severity,
            title=f"주문 급증 감지: 최근 10분간 {rate_10min}건 (평소 대비 {pct}%)",
            description=(
                f"최근 10분간 {rate_10min}건의 주문이 유입되었습니다. "
                f"1시간 평균({avg_10min:.1f}건/10분) 대비 {ratio:.1f}배입니다. "
                f"창고 처리 용량 초과 가능성을 점검해야 합니다."
            ),
            payload={
                "rate_10min": rate_10min,
                "avg_10min": round(avg_10min, 1),
                "ratio": round(ratio, 2),
            },
        )


class VehicleBreakdownRule:
    """
    차량 고장 감지.
    차량 상태가 BREAKDOWN인 차량이 있으면 즉시 감지.
    """

    rule_id = "vehicle_breakdown"

    def check(self, state: StateSnapshot) -> AnomalyEvent | None:
        breakdown_vehicles = [
            v for v in state.vehicle_statuses.values()
            if v.get("status") == "BREAKDOWN"
        ]

        if not breakdown_vehicles:
            return None

        codes = [v["code"] for v in breakdown_vehicles]
        return AnomalyEvent(
            event_type="VEHICLE_BREAKDOWN",
            severity=EventSeverity.CRITICAL,
            title=f"차량 고장 감지: {', '.join(codes)}",
            description=(
                f"{len(breakdown_vehicles)}대의 차량이 고장 상태입니다: {', '.join(codes)}. "
                f"배송 일정 재조정 및 대체 차량 배정이 필요합니다."
            ),
            payload={
                "breakdown_vehicles": breakdown_vehicles,
                "count": len(breakdown_vehicles),
            },
        )


class StockShortageRule:
    """
    재고 부족 감지.
    available_qty < safety_stock 인 항목 발생 시 STOCK_SHORTAGE.
    - available_qty == 0: CRITICAL
    - 그 외: WARNING
    """

    rule_id = "stock_shortage"

    def check(self, state: StateSnapshot) -> AnomalyEvent | None:
        if not state.low_stock_items:
            return None

        zero_stock = {k: v for k, v in state.low_stock_items.items() if v == 0}
        has_critical = len(zero_stock) > 0
        severity = EventSeverity.CRITICAL if has_critical else EventSeverity.WARNING

        return AnomalyEvent(
            event_type="STOCK_SHORTAGE",
            severity=severity,
            title=f"재고 부족 감지: {len(state.low_stock_items)}개 SKU (재고 소진 {len(zero_stock)}개)",
            description=(
                f"안전재고 이하인 SKU가 {len(state.low_stock_items)}개 있습니다. "
                f"이 중 {len(zero_stock)}개는 재고가 완전히 소진되었습니다. "
                f"긴급 보충이 필요합니다."
            ),
            payload={
                "total_low_stock": len(state.low_stock_items),
                "zero_stock_count": len(zero_stock),
                "items": [
                    {"warehouse_id": k[0], "product_id": k[1], "available_qty": v}
                    for k, v in list(state.low_stock_items.items())[:20]
                ],
            },
        )


class SlaRiskRule:
    """
    SLA 위반 위험 감지.
    남은 시간이 SLA의 30% 미만이고, 아직 초기 상태(RECEIVED/PICKING)인 주문.
    - 남은 시간 비율 < 10%: CRITICAL
    - 남은 시간 비율 < 30%: WARNING
    """

    rule_id = "sla_risk"

    def check(self, state: StateSnapshot) -> AnomalyEvent | None:
        if not state.sla_at_risk_orders:
            return None

        critical_orders = [
            o for o in state.sla_at_risk_orders.values()
            if o.get("remaining_ratio", 1.0) < 0.1
        ]
        severity = EventSeverity.CRITICAL if critical_orders else EventSeverity.WARNING

        order_summaries = [
            f"{o['order_code']} ({o.get('customer_name', 'N/A')}, "
            f"남은 {o.get('remaining_ratio', 0) * 100:.0f}%)"
            for o in list(state.sla_at_risk_orders.values())[:5]
        ]

        return AnomalyEvent(
            event_type="SLA_RISK",
            severity=severity,
            title=f"SLA 위반 위험: {len(state.sla_at_risk_orders)}건 주문",
            description=(
                f"납기 SLA 위반 위험이 있는 주문이 {len(state.sla_at_risk_orders)}건입니다. "
                f"해당 주문: {'; '.join(order_summaries)}. "
                f"우선순위 상향 또는 배송 경로 최적화가 필요합니다."
            ),
            payload={
                "at_risk_count": len(state.sla_at_risk_orders),
                "critical_count": len(critical_orders),
                "orders": list(state.sla_at_risk_orders.values())[:10],
            },
        )


class DockCongestionRule:
    """
    도크 혼잡 감지.
    dock_occupancy > 0.9 이면 DOCK_CONGESTION.
    - > 0.95: CRITICAL
    - > 0.9: WARNING
    """

    rule_id = "dock_congestion"

    def check(self, state: StateSnapshot) -> AnomalyEvent | None:
        congested = {
            wh_id: occ for wh_id, occ in state.dock_occupancy.items()
            if occ > 0.9
        }

        if not congested:
            return None

        has_critical = any(occ > 0.95 for occ in congested.values())
        severity = EventSeverity.CRITICAL if has_critical else EventSeverity.WARNING

        wh_info = [f"창고#{wh_id} ({occ * 100:.0f}%)" for wh_id, occ in congested.items()]

        return AnomalyEvent(
            event_type="DOCK_CONGESTION",
            severity=severity,
            title=f"도크 혼잡 감지: {', '.join(wh_info)}",
            description=(
                f"{len(congested)}개 창고에서 도크 점유율이 90%를 초과했습니다. "
                f"출하 대기 시간 증가가 예상됩니다. "
                f"도크 배정 최적화 또는 출하 일정 분산이 필요합니다."
            ),
            payload={
                "congested_warehouses": [
                    {"warehouse_id": wh_id, "occupancy": round(occ, 3)}
                    for wh_id, occ in congested.items()
                ],
            },
        )


# 모든 규칙 인스턴스
ALL_RULES: list[AnomalyRule] = [
    OrderSurgeRule(),
    VehicleBreakdownRule(),
    StockShortageRule(),
    SlaRiskRule(),
    DockCongestionRule(),
]
