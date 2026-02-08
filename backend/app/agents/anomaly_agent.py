"""
Anomaly Agent — OODA Orient 단계.
감지된 이상의 원인을 분석하고 영향 범위를 산정한다.
LLM(Claude API)으로 추론하되, 실패 시 템플릿 기반 fallback.
"""

import json
import time
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Order, Customer, Inventory, Vehicle, Warehouse, Product
from app.models.order import OrderStatus
from app.models.vehicle import VehicleStatus
from app.models.agent_event import AgentType, OODAPhase, EventSeverity
from app.agents.event_logger import AgentEventLogger
from app.agents import llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 한국타이어 출하 물류 전문가 AI입니다.
물류센터에서 발생한 이상 상황의 원인을 분석하고, 영향 범위와 심각도를 평가합니다.

반드시 아래 JSON 형식으로만 응답하세요:
{
  "cause": "이상 상황의 추정 원인 (한국어, 2~3문장)",
  "impact_summary": "영향 범위 요약 (한국어, 2~3문장)",
  "affected_order_count": 숫자,
  "affected_warehouses": ["WH-XXX", ...],
  "recommended_actions": [
    {"action": "액션명", "reason": "이유", "priority": "HIGH/MEDIUM/LOW"},
    ...
  ],
  "severity_assessment": "CRITICAL 또는 WARNING 또는 INFO",
  "confidence": 0.0~1.0
}"""


class AnomalyAgent:
    """Anomaly Agent — 이상 원인 분석 (OODA: Orient)"""

    def __init__(self):
        self.event_logger = AgentEventLogger()

    async def analyze(self, anomaly_event: dict, parent_event_id: str | None = None) -> dict:
        """
        이상 이벤트를 분석한다.
        Returns: 분석 결과 dict
        """
        start = time.monotonic()
        event_type = anomaly_event.get("type", "UNKNOWN")
        logger.info(f"[Anomaly] 원인 분석 시작: {event_type}")

        # 1. 컨텍스트 수집
        loop = asyncio.get_event_loop()
        context = await loop.run_in_executor(None, self._collect_context, anomaly_event)
        logger.info(f"[Anomaly] 컨텍스트 수집 완료")

        # 2. LLM 분석 시도
        analysis = await self._llm_analyze(event_type, anomaly_event, context)

        # 3. LLM 실패 시 템플릿 fallback
        if analysis is None:
            analysis = self._template_fallback(event_type, anomaly_event, context)
            logger.info(f"[Anomaly] 템플릿 Fallback 분석 사용")

        duration_ms = int((time.monotonic() - start) * 1000)

        # 4. agent_events에 기록
        await self.event_logger.log_event(
            agent_type=AgentType.ANOMALY,
            ooda_phase=OODAPhase.ORIENT,
            event_type=event_type,
            severity=EventSeverity[analysis.get("severity_assessment", "WARNING")],
            title=f"원인 분석 완료: {event_type}",
            description=analysis.get("impact_summary", ""),
            payload={"anomaly_event": anomaly_event, "analysis": analysis, "context_summary": context.get("summary", {})},
            reasoning=analysis.get("cause", ""),
            confidence=analysis.get("confidence", 0.5),
            parent_event_id=parent_event_id,
            duration_ms=duration_ms,
        )

        logger.info(
            f"[Anomaly] 분석 완료: {event_type} "
            f"({duration_ms}ms, confidence={analysis.get('confidence', 0):.2f})"
        )

        # WebSocket 브로드캐스트
        from app.api.websocket import broadcast_event
        await broadcast_event("agent_event", {
            "agent_type": "ANOMALY",
            "ooda_phase": "ORIENT",
            "event_type": event_type,
            "title": f"원인 분석 완료: {event_type}",
            "reasoning": analysis.get("cause", ""),
        })

        return analysis

    async def _llm_analyze(self, event_type: str, anomaly_event: dict, context: dict) -> dict | None:
        """LLM으로 원인 분석"""
        if not llm_client.is_available():
            return None

        user_prompt = f"""다음 물류 이상 상황을 분석해주세요.

## 이상 이벤트
- 유형: {event_type}
- 심각도: {anomaly_event.get('severity', 'N/A')}
- 상세: {json.dumps(anomaly_event.get('payload', anomaly_event.get('detail', {})), ensure_ascii=False, default=str)}

## 현재 시스템 상태
- 미처리 주문: {context.get('summary', {}).get('pending_orders', 0)}건
- 최근 1시간 주문: {context.get('summary', {}).get('orders_last_hour', 0)}건
- 안전재고 이하 SKU: {context.get('summary', {}).get('low_stock_count', 0)}개
- 가용 차량: {context.get('summary', {}).get('available_vehicles', 0)}대 / 전체 {context.get('summary', {}).get('total_vehicles', 0)}대
- 고장 차량: {context.get('summary', {}).get('breakdown_vehicles', 0)}대
- 영향받는 주문 목록: {json.dumps(context.get('affected_orders', [])[:5], ensure_ascii=False, default=str)}
- 창고별 도크 점유: {json.dumps(context.get('summary', {}).get('dock_occupancy', {}), ensure_ascii=False, default=str)}

JSON 형식으로만 응답하세요."""

        text = await llm_client.call_llm(SYSTEM_PROMPT, user_prompt)
        if text is None:
            return None

        try:
            # JSON 추출 (코드블록 안에 있을 수 있음)
            cleaned = text.strip()
            if "```" in cleaned:
                start_idx = cleaned.find("{")
                end_idx = cleaned.rfind("}") + 1
                cleaned = cleaned[start_idx:end_idx]
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"LLM 응답 JSON 파싱 실패: {e}")
            return None

    def _template_fallback(self, event_type: str, anomaly_event: dict, context: dict) -> dict:
        """LLM 없을 때 템플릿 기반 분석"""
        summary = context.get("summary", {})
        pending = summary.get("pending_orders", 0)
        affected = context.get("affected_orders", [])

        templates = {
            "ORDER_SURGE": {
                "cause": (
                    f"주문 유입률이 급증했습니다. "
                    f"프로모션, 계절적 수요 증가, 또는 대형 거래처의 일괄 발주가 원인으로 추정됩니다. "
                    f"현재 미처리 주문 {pending}건이 적체되어 있습니다."
                ),
                "impact_summary": (
                    f"창고 처리 용량 대비 주문량이 초과하여 출하 지연이 발생할 수 있습니다. "
                    f"VIP 고객 주문의 SLA 위반 위험이 높아지고, 피킹/패킹 인력 부족이 예상됩니다."
                ),
                "recommended_actions": [
                    {"action": "피킹 순서 재조정", "reason": "VIP 주문 우선 처리", "priority": "HIGH"},
                    {"action": "ECONOMY 주문 익일 전환", "reason": "처리 용량 확보", "priority": "MEDIUM"},
                    {"action": "추가 차량 배차", "reason": "출하량 증가 대응", "priority": "MEDIUM"},
                ],
                "severity_assessment": "CRITICAL",
                "confidence": 0.75,
            },
            "VEHICLE_BREAKDOWN": {
                "cause": (
                    f"차량 고장이 발생했습니다. "
                    f"현재 가용 차량 {summary.get('available_vehicles', 0)}대로 배송 수행 중이며, "
                    f"고장 차량의 배송 건을 재배정해야 합니다."
                ),
                "impact_summary": (
                    f"해당 차량에 배정된 주문의 배송이 지연될 수 있습니다. "
                    f"특히 VIP 고객 주문이 포함된 경우 SLA 위반 위험이 있습니다."
                ),
                "recommended_actions": [
                    {"action": "배차 재배정", "reason": "고장 차량 대체", "priority": "HIGH"},
                    {"action": "고객 알림 발송", "reason": "배송 지연 사전 안내", "priority": "HIGH"},
                    {"action": "경로 재최적화", "reason": "대체 차량 경로 설정", "priority": "MEDIUM"},
                ],
                "severity_assessment": "CRITICAL",
                "confidence": 0.80,
            },
            "STOCK_SHORTAGE": {
                "cause": (
                    f"안전재고 이하인 SKU가 {summary.get('low_stock_count', 0)}개 발생했습니다. "
                    f"수요 급증 또는 공급 지연이 원인으로 추정됩니다."
                ),
                "impact_summary": (
                    f"해당 SKU가 포함된 주문의 출하가 지연될 수 있습니다. "
                    f"대체 창고에서의 재고 이동 또는 긴급 생산 요청이 필요할 수 있습니다."
                ),
                "recommended_actions": [
                    {"action": "긴급 생산 요청", "reason": "재고 소진 품목 보충", "priority": "HIGH"},
                    {"action": "대체 창고 재고 이동", "reason": "다른 창고의 여유 재고 활용", "priority": "MEDIUM"},
                    {"action": "주문 부분 출하", "reason": "가용 품목 먼저 배송", "priority": "LOW"},
                ],
                "severity_assessment": "WARNING",
                "confidence": 0.70,
            },
            "SLA_RISK": {
                "cause": (
                    f"VIP 고객 주문의 납기 위반 위험이 감지되었습니다. "
                    f"주문 적체, 재고 부족, 또는 차량 부족으로 인해 처리가 지연되고 있습니다."
                ),
                "impact_summary": (
                    f"SLA 위반 시 고객사와의 계약 위반에 해당하며, "
                    f"거래 관계 악화 및 패널티 발생 가능성이 있습니다."
                ),
                "recommended_actions": [
                    {"action": "피킹 순서 변경", "reason": "위험 주문 최우선 처리", "priority": "HIGH"},
                    {"action": "고객 알림 발송", "reason": "지연 가능성 사전 안내", "priority": "HIGH"},
                    {"action": "경로 재최적화", "reason": "배송 시간 단축", "priority": "MEDIUM"},
                ],
                "severity_assessment": "CRITICAL",
                "confidence": 0.80,
            },
            "DOCK_CONGESTION": {
                "cause": (
                    f"도크 점유율이 높아 출하 대기 시간이 증가하고 있습니다. "
                    f"동시 출하 건수 증가 또는 적재 시간 초과가 원인으로 추정됩니다."
                ),
                "impact_summary": (
                    f"도크 혼잡으로 인해 전체 출하 처리 시간이 증가합니다. "
                    f"연쇄적으로 배송 지연이 발생할 수 있습니다."
                ),
                "recommended_actions": [
                    {"action": "피킹 순서 변경", "reason": "도크 사용 효율화", "priority": "HIGH"},
                    {"action": "ECONOMY 주문 익일 전환", "reason": "도크 부하 분산", "priority": "MEDIUM"},
                ],
                "severity_assessment": "WARNING",
                "confidence": 0.70,
            },
        }

        result = templates.get(event_type, {
            "cause": f"{event_type} 이상 상황이 감지되었습니다.",
            "impact_summary": f"미처리 주문 {pending}건에 영향이 예상됩니다.",
            "recommended_actions": [{"action": "상황 모니터링", "reason": "추가 데이터 수집", "priority": "MEDIUM"}],
            "severity_assessment": "WARNING",
            "confidence": 0.50,
        })

        result["affected_order_count"] = len(affected)
        result["affected_warehouses"] = summary.get("warehouse_codes", [])
        return result

    def _collect_context(self, anomaly_event: dict) -> dict:
        """이상 분석을 위한 컨텍스트 수집 (블로킹 DB 쿼리)"""
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            one_hour_ago = now - timedelta(hours=1)

            # 미처리 주문
            pending_orders = (
                db.query(Order)
                .filter(Order.status.in_([OrderStatus.RECEIVED, OrderStatus.PICKING]))
                .all()
            )

            # 최근 1시간 주문
            recent_orders = (
                db.query(func.count(Order.id))
                .filter(Order.created_at >= one_hour_ago)
                .scalar() or 0
            )

            # 안전재고 이하 SKU
            low_stock = (
                db.query(Inventory)
                .filter(Inventory.available_qty <= Inventory.safety_stock)
                .all()
            )

            # 차량 현황
            vehicles = db.query(Vehicle).all()
            available = sum(1 for v in vehicles if v.status == VehicleStatus.AVAILABLE)
            breakdown = sum(1 for v in vehicles if v.status == VehicleStatus.BREAKDOWN)

            # 창고 도크 점유
            warehouses = db.query(Warehouse).all()
            dock_occ = {}
            wh_codes = []
            for wh in warehouses:
                loading = sum(1 for v in vehicles
                              if v.warehouse_id == wh.id and v.status == VehicleStatus.LOADING)
                dock_occ[wh.code] = round(loading / wh.dock_count, 2) if wh.dock_count > 0 else 0
                wh_codes.append(wh.code)

            # 영향받는 주문 (상위 10건)
            affected_orders = []
            for o in sorted(pending_orders, key=lambda x: x.priority_score, reverse=True)[:10]:
                customer = db.query(Customer).get(o.customer_id)
                affected_orders.append({
                    "order_code": o.order_code,
                    "customer": customer.name if customer else "N/A",
                    "grade": customer.grade.value if customer else "N/A",
                    "priority": o.priority_score,
                    "status": o.status.value,
                })

            return {
                "summary": {
                    "pending_orders": len(pending_orders),
                    "orders_last_hour": recent_orders,
                    "low_stock_count": len(low_stock),
                    "available_vehicles": available,
                    "total_vehicles": len(vehicles),
                    "breakdown_vehicles": breakdown,
                    "dock_occupancy": dock_occ,
                    "warehouse_codes": wh_codes,
                },
                "affected_orders": affected_orders,
            }
        finally:
            db.close()
