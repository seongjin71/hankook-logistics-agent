"""
OODA 오케스트레이터 — Monitor → Anomaly → Priority → Action 파이프라인.
LangGraph 없이 순차 async 함수 호출로 구현한다.
각 단계의 입출력이 agent_events에 기록된다.
"""

import logging
import time

from app.events.event_bus import AsyncEventBus
from app.agents.anomaly_agent import AnomalyAgent
from app.agents.priority_agent import PriorityAgent
from app.agents.action_agent import ActionAgent

logger = logging.getLogger(__name__)


class OODAOrchestrator:
    """
    OODA 루프 오케스트레이터.

    Monitor Agent가 anomaly.detected 이벤트를 발행하면,
    이 오케스트레이터가 나머지 파이프라인(Orient → Decide → Act)을 실행한다.
    """

    def __init__(self, event_bus: AsyncEventBus):
        self.event_bus = event_bus
        self.anomaly_agent = AnomalyAgent()
        self.priority_agent = PriorityAgent()
        self.action_agent = ActionAgent()

    async def start(self):
        """anomaly.detected 이벤트 구독"""
        await self.event_bus.subscribe("anomaly.detected", self._on_anomaly_detected)
        logger.info("OODA Orchestrator 시작 — anomaly.detected 구독 등록")

    async def _on_anomaly_detected(self, topic: str, data: dict):
        """
        Monitor Agent → 이상 감지 이벤트 수신.
        source=monitor_agent인 이벤트만 파이프라인을 실행한다.
        (수동 트리거 등 다른 소스는 별도 처리 가능)
        """
        source = data.get("source", "")
        event_type = data.get("type", "UNKNOWN")
        parent_event_id = data.get("event_id")

        # monitor_agent 또는 manual_trigger에서 온 이벤트만 처리
        if source not in ("monitor_agent", "manual_trigger"):
            return

        logger.info(f"[Orchestrator] OODA 파이프라인 시작: {event_type} (source={source})")
        start = time.monotonic()

        try:
            # ── Orient: 원인 분석 ──
            analysis = await self.anomaly_agent.analyze(data, parent_event_id=parent_event_id)
            analysis["event_type"] = event_type
            # affected_orders를 context에서 가져옴
            if "affected_orders" not in analysis and "payload" in data:
                analysis["affected_orders"] = data["payload"].get("affected_orders", [])

            # ── Decide: 우선순위 재계산 ──
            priority_result = await self.priority_agent.recalculate(
                analysis, parent_event_id=parent_event_id
            )

            # ── Act: 액션 실행 ──
            action_results = await self.action_agent.execute(
                analysis, priority_result, parent_event_id=parent_event_id
            )

            elapsed = int((time.monotonic() - start) * 1000)
            logger.info(
                f"[Orchestrator] OODA 파이프라인 완료: {event_type} "
                f"(분석→재계산→액션 {elapsed}ms)"
            )

        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error(f"[Orchestrator] 파이프라인 에러: {event_type} ({elapsed}ms) — {e}")

    async def run_pipeline(self, anomaly_event: dict) -> dict:
        """
        외부에서 직접 파이프라인을 실행할 때 사용.
        Returns: 전체 파이프라인 결과
        """
        event_type = anomaly_event.get("type", "UNKNOWN")
        parent_event_id = anomaly_event.get("event_id")

        # Orient
        analysis = await self.anomaly_agent.analyze(anomaly_event, parent_event_id=parent_event_id)
        analysis["event_type"] = event_type

        # Decide
        priority_result = await self.priority_agent.recalculate(
            analysis, parent_event_id=parent_event_id
        )

        # Act
        action_results = await self.action_agent.execute(
            analysis, priority_result, parent_event_id=parent_event_id
        )

        return {
            "event_type": event_type,
            "analysis": analysis,
            "priority_result": priority_result,
            "action_results": action_results,
        }
