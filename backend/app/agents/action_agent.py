"""
Action Agent — OODA Act 단계.
Priority Agent의 결정을 받아 구체적 액션을 실행하거나 에스컬레이션한다.
confidence + 액션 유형에 따라 AUTO / PENDING_APPROVAL / ESCALATED 결정.
"""

import time
import asyncio
import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models import Order
from app.models.order import OrderStatus
from app.models.agent_event import (
    AgentType, OODAPhase, EventSeverity, ExecutionMode,
)
from app.agents.event_logger import AgentEventLogger

logger = logging.getLogger(__name__)

# 액션별 confidence 임계치
# (action_type, auto_threshold, approval_threshold)
# auto >= threshold → AUTO, approval >= threshold → PENDING_APPROVAL, else ESCALATED
ACTION_THRESHOLDS = {
    "피킹 순서 변경":     (0.85, 0.60),
    "주문 익일 전환":     (0.85, 0.60),
    "배차 재배정":         (1.01, 0.60),   # 1.01 = 자동 실행 없음 (항상 승인 필요)
    "경로 재최적화":       (0.85, 0.60),
    "긴급 생산 요청":     (1.01, 1.01),   # 항상 에스컬레이션
    "고객 알림 발송":     (0.60, 0.30),   # 낮은 임계치
    "ECONOMY 주문 익일 전환": (0.85, 0.60),
    "대체 창고 재고 이동": (1.01, 0.60),
    "주문 부분 출하":     (0.85, 0.60),
    "도크 사용 효율화":   (0.85, 0.60),
    "상황 모니터링":       (0.50, 0.30),
}


def _determine_execution_mode(action_type: str, confidence: float) -> ExecutionMode:
    """액션 유형과 confidence에 따라 실행 모드 결정"""
    auto_th, approval_th = ACTION_THRESHOLDS.get(action_type, (0.85, 0.60))

    if confidence >= auto_th:
        return ExecutionMode.AUTO
    elif confidence >= approval_th:
        return ExecutionMode.PENDING_APPROVAL
    else:
        return ExecutionMode.ESCALATED


class ActionAgent:
    """Action Agent — 액션 실행/에스컬레이션 (OODA: Act)"""

    def __init__(self):
        self.event_logger = AgentEventLogger()

    async def execute(self, analysis: dict, priority_result: dict,
                      parent_event_id: str | None = None) -> list[dict]:
        """
        분석 결과와 우선순위 결과를 받아 액션을 결정하고 실행한다.
        Returns: 액션 실행 결과 리스트
        """
        start = time.monotonic()
        event_type = analysis.get("event_type", "UNKNOWN")

        # recommended_actions에서 액션 목록 추출
        recommended = analysis.get("recommended_actions", [])
        confidence = analysis.get("confidence", 0.5)

        if not recommended:
            recommended = [{"action": "상황 모니터링", "reason": "추가 데이터 수집 필요", "priority": "LOW"}]

        logger.info(f"[Action] 액션 실행 시작: {len(recommended)}개 액션 (confidence={confidence:.2f})")

        results = []
        for rec in recommended:
            action_type = rec.get("action", "상황 모니터링")
            reason = rec.get("reason", "")
            action_priority = rec.get("priority", "MEDIUM")

            exec_mode = _determine_execution_mode(action_type, confidence)

            # 액션별 실행
            action_result = await self._execute_action(
                action_type=action_type,
                exec_mode=exec_mode,
                reason=reason,
                confidence=confidence,
                event_type=event_type,
                priority_result=priority_result,
                parent_event_id=parent_event_id,
            )

            results.append(action_result)

            mode_label = {
                ExecutionMode.AUTO: "자동 실행",
                ExecutionMode.PENDING_APPROVAL: "승인 대기",
                ExecutionMode.ESCALATED: "에스컬레이션",
            }.get(exec_mode, str(exec_mode))

            logger.info(
                f"[Action] {mode_label}: {action_type} "
                f"(confidence: {confidence:.2f}, reason: {reason})"
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        # WebSocket 브로드캐스트
        from app.api.websocket import broadcast_event
        auto_count = sum(1 for r in results if r.get("execution_mode") == "AUTO")
        pending_count = sum(1 for r in results if r.get("execution_mode") == "PENDING_APPROVAL")
        escalated_count = sum(1 for r in results if r.get("execution_mode") == "ESCALATED")

        await broadcast_event("agent_event", {
            "agent_type": "ACTION",
            "ooda_phase": "ACT",
            "event_type": event_type,
            "title": f"액션 처리 완료: 자동 {auto_count}건, 승인대기 {pending_count}건, 에스컬 {escalated_count}건",
        })

        return results

    async def _execute_action(
        self,
        action_type: str,
        exec_mode: ExecutionMode,
        reason: str,
        confidence: float,
        event_type: str,
        priority_result: dict,
        parent_event_id: str | None,
    ) -> dict:
        """개별 액션 실행 및 기록"""

        action_taken = None
        action_detail = {}

        if exec_mode == ExecutionMode.AUTO:
            # 자동 실행 — 실제 DB 상태 변경
            loop = asyncio.get_event_loop()
            action_detail = await loop.run_in_executor(
                None, self._perform_action, action_type, priority_result
            )
            action_taken = f"{action_type} 자동 실행 완료"

        elif exec_mode == ExecutionMode.PENDING_APPROVAL:
            action_taken = f"{action_type} — 관리자 승인 대기"
            action_detail = {
                "action_type": action_type,
                "reason": reason,
                "awaiting_approval": True,
            }

        elif exec_mode == ExecutionMode.ESCALATED:
            action_taken = f"{action_type} — 에스컬레이션 (관리자 판단 필요)"
            action_detail = {
                "action_type": action_type,
                "reason": reason,
                "escalated": True,
            }

        # agent_events에 기록
        severity = EventSeverity.INFO if exec_mode == ExecutionMode.AUTO else EventSeverity.WARNING
        event = await self.event_logger.log_event(
            agent_type=AgentType.ACTION,
            ooda_phase=OODAPhase.ACT,
            event_type=event_type,
            severity=severity,
            title=action_taken or action_type,
            description=f"액션: {action_type} | 사유: {reason} | 모드: {exec_mode.value}",
            payload={
                "action_type": action_type,
                "reason": reason,
                "confidence": confidence,
                "execution_mode": exec_mode.value,
                "detail": action_detail,
            },
            confidence=confidence,
            action_taken=action_taken,
            execution_mode=exec_mode,
            parent_event_id=parent_event_id,
        )

        return {
            "event_id": event.event_id,
            "action_type": action_type,
            "execution_mode": exec_mode.value,
            "reason": reason,
            "confidence": confidence,
            "action_taken": action_taken,
            "detail": action_detail,
        }

    def _perform_action(self, action_type: str, priority_result: dict) -> dict:
        """실제 액션 수행 (블로킹 DB 작업)"""
        db = SessionLocal()
        try:
            result = {}

            if action_type in ("피킹 순서 변경", "피킹 순서 재조정"):
                # 우선순위 재계산 결과에 따라 상위 주문 상태를 PICKING으로 변경
                changes = priority_result.get("changes", [])
                upgraded_codes = [c["order_code"] for c in changes if c.get("direction") == "상향"][:5]
                updated = 0
                for code in upgraded_codes:
                    order = db.query(Order).filter(Order.order_code == code).first()
                    if order and order.status == OrderStatus.RECEIVED:
                        order.status = OrderStatus.PICKING
                        order.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                        updated += 1
                db.commit()
                result = {"orders_moved_to_picking": updated, "order_codes": upgraded_codes}

            elif action_type in ("주문 익일 전환", "ECONOMY 주문 익일 전환"):
                # 낮은 우선순위 ECONOMY 주문 — 실제로는 상태 변경 없이 기록만
                result = {"note": "ECONOMY 주문 익일 전환 처리 기록"}

            elif action_type == "고객 알림 발송":
                result = {"note": "고객 알림 발송 시뮬레이션 완료"}

            elif action_type == "경로 재최적화":
                result = {"note": "경로 재최적화 시뮬레이션 완료"}

            elif action_type == "상황 모니터링":
                result = {"note": "모니터링 지속"}

            elif action_type == "도크 사용 효율화":
                result = {"note": "도크 배정 효율화 시뮬레이션 완료"}

            else:
                result = {"note": f"{action_type} 시뮬레이션 완료"}

            return result

        except Exception as e:
            db.rollback()
            logger.error(f"액션 수행 실패 ({action_type}): {e}")
            return {"error": str(e)}
        finally:
            db.close()

    async def approve_action(self, event_id: str) -> dict:
        """PENDING_APPROVAL 액션을 승인하여 실행"""
        from app.models import AgentEvent
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._do_approve, event_id)

    def _do_approve(self, event_id: str) -> dict:
        """승인 처리 (블로킹)"""
        from app.models import AgentEvent
        db = SessionLocal()
        try:
            event = db.query(AgentEvent).filter(AgentEvent.event_id == event_id).first()
            if not event:
                return {"error": "이벤트를 찾을 수 없습니다", "event_id": event_id}

            if event.execution_mode != ExecutionMode.PENDING_APPROVAL:
                return {"error": f"승인 대기 상태가 아닙니다 (현재: {event.execution_mode})", "event_id": event_id}

            # 승인 처리
            event.execution_mode = ExecutionMode.HUMAN_APPROVED
            event.action_taken = f"{event.action_taken} → 관리자 승인 완료"
            db.commit()

            logger.info(f"[Action] 액션 승인: {event_id} — {event.payload.get('action_type', '')}")
            return {
                "event_id": event_id,
                "status": "approved",
                "action_type": event.payload.get("action_type", "") if event.payload else "",
            }
        except Exception as e:
            db.rollback()
            logger.error(f"승인 처리 실패: {e}")
            return {"error": str(e)}
        finally:
            db.close()

    async def reject_action(self, event_id: str, reason: str = "") -> dict:
        """PENDING_APPROVAL 액션을 거절"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._do_reject, event_id, reason)

    def _do_reject(self, event_id: str, reason: str) -> dict:
        """거절 처리 (블로킹)"""
        from app.models import AgentEvent
        db = SessionLocal()
        try:
            event = db.query(AgentEvent).filter(AgentEvent.event_id == event_id).first()
            if not event:
                return {"error": "이벤트를 찾을 수 없습니다"}

            if event.execution_mode != ExecutionMode.PENDING_APPROVAL:
                return {"error": f"승인 대기 상태가 아닙니다 (현재: {event.execution_mode})"}

            # 거절 기록
            event.execution_mode = ExecutionMode.ESCALATED
            event.action_taken = f"{event.action_taken} → 관리자 거절: {reason}"
            if event.payload:
                event.payload = {**event.payload, "rejected": True, "reject_reason": reason}
            db.commit()

            logger.info(f"[Action] 액션 거절: {event_id} — {reason}")
            return {"event_id": event_id, "status": "rejected", "reason": reason}
        except Exception as e:
            db.rollback()
            logger.error(f"거절 처리 실패: {e}")
            return {"error": str(e)}
        finally:
            db.close()
