"""
에이전트 API — AI 에이전트 이벤트 로그 조회, 타임라인
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import AgentEvent

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/events")
def list_events(
    agent_type: str | None = Query(None, description="에이전트 타입 필터 (MONITOR, ANOMALY, PRIORITY, ACTION)"),
    ooda_phase: str | None = Query(None, description="OODA 단계 필터 (OBSERVE, ORIENT, DECIDE, ACT)"),
    event_type: str | None = Query(None, description="이벤트 타입 필터"),
    severity: str | None = Query(None, description="심각도 필터 (CRITICAL, WARNING, INFO)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """에이전트 이벤트 로그 목록 조회 (최신순)"""
    query = db.query(AgentEvent)

    if agent_type:
        query = query.filter(AgentEvent.agent_type == agent_type)
    if ooda_phase:
        query = query.filter(AgentEvent.ooda_phase == ooda_phase)
    if event_type:
        query = query.filter(AgentEvent.event_type == event_type)
    if severity:
        query = query.filter(AgentEvent.severity == severity)

    total = query.count()
    events = query.order_by(desc(AgentEvent.created_at)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "events": [_serialize_event(e) for e in events],
    }


@router.get("/timeline")
def get_timeline(
    minutes: int = Query(30, ge=1, le=1440, description="조회할 최근 N분"),
    db: Session = Depends(get_db),
):
    """최근 N분간의 에이전트 이벤트를 타임라인 형식으로 반환"""
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    events = (
        db.query(AgentEvent)
        .filter(AgentEvent.created_at >= since)
        .order_by(desc(AgentEvent.created_at))
        .all()
    )

    return {
        "minutes": minutes,
        "count": len(events),
        "timeline": [
            {
                "timestamp": e.created_at.isoformat() if e.created_at else None,
                "agent_type": _enum_val(e.agent_type),
                "ooda_phase": _enum_val(e.ooda_phase),
                "event_type": e.event_type,
                "severity": _enum_val(e.severity),
                "title": e.title,
                "event_id": e.event_id,
            }
            for e in events
        ],
    }


def _enum_val(v):
    """Enum 값 안전 추출"""
    return v.value if hasattr(v, "value") else str(v) if v else None


def _serialize_event(e: AgentEvent) -> dict:
    """AgentEvent ORM → dict 변환"""
    return {
        "id": e.id,
        "event_id": e.event_id,
        "agent_type": _enum_val(e.agent_type),
        "ooda_phase": _enum_val(e.ooda_phase),
        "event_type": e.event_type,
        "severity": _enum_val(e.severity),
        "title": e.title,
        "description": e.description,
        "payload": e.payload,
        "reasoning": e.reasoning,
        "confidence": e.confidence,
        "action_taken": e.action_taken,
        "execution_mode": _enum_val(e.execution_mode),
        "parent_event_id": e.parent_event_id,
        "duration_ms": e.duration_ms,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
