"""
Human-in-the-loop API — 승인 대기 액션 관리
- GET /api/actions/pending: 승인 대기 액션 목록
- POST /api/actions/{event_id}/approve: 액션 승인
- POST /api/actions/{event_id}/reject: 액션 거절
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import AgentEvent
from app.models.agent_event import ExecutionMode

router = APIRouter(prefix="/api/actions", tags=["actions"])

# Action Agent 싱글턴 (main.py에서 설정)
_action_agent = None


def set_action_agent(agent):
    """main.py에서 호출하여 Action Agent 참조 설정"""
    global _action_agent
    _action_agent = agent


class RejectRequest(BaseModel):
    reason: str = ""


@router.get("/pending")
def list_pending_actions(
    db: Session = Depends(get_db),
):
    """현재 승인 대기 중인 액션 목록"""
    events = (
        db.query(AgentEvent)
        .filter(AgentEvent.execution_mode == ExecutionMode.PENDING_APPROVAL)
        .order_by(desc(AgentEvent.created_at))
        .all()
    )

    return {
        "total": len(events),
        "pending_actions": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "title": e.title,
                "description": e.description,
                "action_type": e.payload.get("action_type", "") if e.payload else "",
                "reason": e.payload.get("reason", "") if e.payload else "",
                "confidence": e.confidence,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.post("/{event_id}/approve")
async def approve_action(event_id: str):
    """PENDING_APPROVAL 액션을 승인하여 실행"""
    if _action_agent is None:
        return {"error": "Action Agent가 초기화되지 않았습니다"}

    result = await _action_agent.approve_action(event_id)

    # WebSocket 알림
    from app.api.websocket import broadcast_event
    await broadcast_event("action_approved", {
        "event_id": event_id,
        "result": result,
    })

    return result


@router.post("/{event_id}/reject")
async def reject_action(event_id: str, req: RejectRequest):
    """PENDING_APPROVAL 액션을 거절"""
    if _action_agent is None:
        return {"error": "Action Agent가 초기화되지 않았습니다"}

    result = await _action_agent.reject_action(event_id, reason=req.reason)
    return result
