"""
WebSocket 엔드포인트 — 실시간 이벤트 Push
클라이언트가 /ws/realtime에 연결하면 다음 이벤트를 실시간으로 push:
  - dashboard_update: 5초마다 대시보드 요약
  - new_order: 새 주문 생성 시
  - anomaly_detected: 이상 감지 시
  - agent_event: 에이전트 활동 시
  - vehicle_update: 차량 상태/위치 변경 시
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func

from app.database import SessionLocal
from app.models import Order, Inventory, Vehicle
from app.models.order import OrderStatus
from app.models.vehicle import VehicleStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 연결: {len(self.active_connections)}개 활성")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket 해제: {len(self.active_connections)}개 활성")

    async def broadcast(self, message: dict):
        """모든 연결된 클라이언트에게 메시지 전송"""
        if not self.active_connections:
            return

        text = json.dumps(message, ensure_ascii=False, default=str)
        disconnected = []
        for ws in self.active_connections:
            try:
                await ws.send_text(text)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self.disconnect(ws)


# 싱글턴 매니저
ws_manager = ConnectionManager()


async def broadcast_event(event_type: str, data: dict):
    """외부에서 호출 가능한 브로드캐스트 헬퍼"""
    await ws_manager.broadcast({
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    })


def _get_dashboard_summary() -> dict:
    """대시보드 요약 데이터 조회 (블로킹)"""
    db = SessionLocal()
    try:
        total_orders = db.query(func.count(Order.id)).scalar() or 0

        status_counts = (
            db.query(Order.status, func.count(Order.id))
            .group_by(Order.status).all()
        )
        by_status = {
            (s.value if hasattr(s, 'value') else str(s)): c
            for s, c in status_counts
        }

        high = db.query(func.count(Order.id)).filter(Order.priority_score > 70).scalar() or 0
        medium = db.query(func.count(Order.id)).filter(
            Order.priority_score >= 40, Order.priority_score <= 70
        ).scalar() or 0
        low = db.query(func.count(Order.id)).filter(Order.priority_score < 40).scalar() or 0

        low_stock = (
            db.query(func.count(Inventory.id))
            .filter(Inventory.available_qty <= Inventory.safety_stock)
            .scalar() or 0
        )

        vehicle_counts = (
            db.query(Vehicle.status, func.count(Vehicle.id))
            .group_by(Vehicle.status).all()
        )
        vehicle_by_status = {
            (s.value if hasattr(s, 'value') else str(s)): c
            for s, c in vehicle_counts
        }

        return {
            "orders": {"total": total_orders, "by_status": by_status,
                       "by_priority": {"HIGH": high, "MEDIUM": medium, "LOW": low}},
            "inventory": {"low_stock_count": low_stock},
            "vehicles": {"by_status": vehicle_by_status},
        }
    finally:
        db.close()


@router.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """실시간 WebSocket 엔드포인트"""
    await ws_manager.connect(websocket)

    try:
        # 대시보드 업데이트를 5초마다 보내는 태스크
        async def dashboard_loop():
            while True:
                try:
                    await asyncio.sleep(5)
                    loop = asyncio.get_event_loop()
                    summary = await loop.run_in_executor(None, _get_dashboard_summary)
                    await websocket.send_text(json.dumps({
                        "type": "dashboard_update",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": summary,
                    }, ensure_ascii=False, default=str))
                except (WebSocketDisconnect, Exception):
                    break

        dashboard_task = asyncio.create_task(dashboard_loop())

        # 클라이언트 메시지 수신 루프 (핑/퐁 유지)
        while True:
            try:
                data = await websocket.receive_text()
                # 클라이언트에서 ping 메시지가 오면 pong 응답
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket 에러: {e}")
    finally:
        dashboard_task.cancel()
        ws_manager.disconnect(websocket)
