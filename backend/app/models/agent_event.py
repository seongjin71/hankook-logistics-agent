"""
agent_events 테이블 — AI 에이전트 활동 로그
- 시각화의 핵심 데이터 소스
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Text, Enum, DateTime, JSON

from app.database import Base


class AgentType(str, enum.Enum):
    MONITOR = "MONITOR"
    ANOMALY = "ANOMALY"
    PRIORITY = "PRIORITY"
    ACTION = "ACTION"


class OODAPhase(str, enum.Enum):
    OBSERVE = "OBSERVE"
    ORIENT = "ORIENT"
    DECIDE = "DECIDE"
    ACT = "ACT"


class EventSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class ExecutionMode(str, enum.Enum):
    AUTO = "AUTO"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ESCALATED = "ESCALATED"


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(36), unique=True, nullable=False)  # UUID
    agent_type = Column(Enum(AgentType), nullable=False)
    ooda_phase = Column(Enum(OODAPhase), nullable=False)
    event_type = Column(String(50), nullable=False)  # "ORDER_SURGE", "VEHICLE_BREAKDOWN" 등
    severity = Column(Enum(EventSeverity), nullable=False)
    title = Column(String(200), nullable=False)  # 이벤트 요약 제목
    description = Column(Text)  # 상세 설명
    payload = Column(JSON)  # 에이전트 입출력 데이터 전체
    reasoning = Column(Text, nullable=True)  # LLM 추론 과정 (자연어)
    confidence = Column(Float, nullable=True)  # 의사결정 신뢰도 (0.0~1.0)
    action_taken = Column(String(200), nullable=True)  # 실행된 액션 요약
    execution_mode = Column(Enum(ExecutionMode), nullable=True)
    parent_event_id = Column(String(36), nullable=True)  # 연쇄 이벤트의 부모
    duration_ms = Column(Integer, nullable=True)  # 처리 소요 시간
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
