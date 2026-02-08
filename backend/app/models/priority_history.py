"""
priority_history 테이블 — 주문 우선순위 변경 이력
- 변경 전후를 기록하여 시각화에 활용한다.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey

from app.database import Base


class PriorityHistory(Base):
    __tablename__ = "priority_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    previous_score = Column(Float, nullable=False)
    new_score = Column(Float, nullable=False)
    reason = Column(String(200), nullable=False)
    agent_event_id = Column(String(36), nullable=True)  # 변경을 트리거한 에이전트 이벤트
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
