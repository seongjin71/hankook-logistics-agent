"""
에이전트 이벤트 로거 — 모든 에이전트 활동을 agent_events 테이블에 기록한다.
- 비동기 인터페이스
- 블로킹 DB 작업은 run_in_executor로 실행
"""

import asyncio
import uuid
import time
import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.agent_event import (
    AgentEvent, AgentType, OODAPhase, EventSeverity, ExecutionMode,
)

logger = logging.getLogger(__name__)


class AgentEventLogger:
    """에이전트 이벤트 로거 — agent_events 테이블에 기록"""

    async def log_event(
        self,
        agent_type: AgentType,
        ooda_phase: OODAPhase,
        event_type: str,
        severity: EventSeverity,
        title: str,
        description: str,
        payload: dict | None = None,
        reasoning: str | None = None,
        confidence: float | None = None,
        action_taken: str | None = None,
        execution_mode: ExecutionMode | None = None,
        parent_event_id: str | None = None,
        duration_ms: int | None = None,
    ) -> AgentEvent:
        """에이전트 이벤트를 DB에 기록하고 반환한다."""
        event_id = str(uuid.uuid4())
        start = time.monotonic()

        event = AgentEvent(
            event_id=event_id,
            agent_type=agent_type,
            ooda_phase=ooda_phase,
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            payload=payload,
            reasoning=reasoning,
            confidence=confidence,
            action_taken=action_taken,
            execution_mode=execution_mode,
            parent_event_id=parent_event_id,
            duration_ms=duration_ms,
            created_at=datetime.now(timezone.utc),
        )

        # DB 기록은 블로킹이므로 executor에서 실행
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_to_db, event)

        elapsed = int((time.monotonic() - start) * 1000)
        logger.info(
            f"[AgentEvent] {agent_type.value}/{ooda_phase.value} "
            f"| {event_type} [{severity.value}] | {title} ({elapsed}ms)"
        )

        return event

    def _save_to_db(self, event: AgentEvent):
        """블로킹 DB 저장"""
        db = SessionLocal()
        try:
            db.add(event)
            db.commit()
            db.refresh(event)
        except Exception as e:
            db.rollback()
            logger.error(f"에이전트 이벤트 DB 저장 실패: {e}")
            raise
        finally:
            db.close()
