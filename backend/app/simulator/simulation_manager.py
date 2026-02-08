"""
시뮬레이션 매니저 — 백그라운드 태스크로 주문 생성, 차량 업데이트를 관리한다.
- AsyncEventBus와 연동하여 이벤트 발행
- 속도 조절 (1x, 5x, 10x) 지원
- FastAPI lifespan에서 시작
"""

import asyncio
import logging

from app.config import settings
from app.events.event_bus import AsyncEventBus
from app.simulator.event_bus import EventBus
from app.simulator.order_simulator import OrderSimulator
from app.simulator.vehicle_simulator import VehicleSimulator
from app.simulator.anomaly_injector import AnomalyInjector

logger = logging.getLogger(__name__)


class SimulationManager:
    """시뮬레이션 전체 라이프사이클 관리"""

    def __init__(self):
        # 동기 이벤트 버스 (시뮬레이터 내부용 — 기존 호환)
        self._sync_event_bus = EventBus(settings.REDIS_URL)

        # 비동기 이벤트 버스 (Phase 2 — Monitor Agent 등과 연동)
        self.async_event_bus: AsyncEventBus | None = None

        self.order_simulator = OrderSimulator(self._sync_event_bus)
        self.vehicle_simulator = VehicleSimulator(self._sync_event_bus)
        self.anomaly_injector = AnomalyInjector(self._sync_event_bus, self.order_simulator)

        self._speed: int = settings.SIMULATION_DEFAULT_SPEED
        self._running: bool = False
        self._tasks: list[asyncio.Task] = []

    def set_async_event_bus(self, bus: AsyncEventBus):
        """비동기 이벤트 버스를 설정한다 (main.py에서 호출)."""
        self.async_event_bus = bus

    @property
    def speed(self) -> int:
        return self._speed

    @speed.setter
    def speed(self, value: int):
        if value not in (1, 5, 10):
            raise ValueError("속도는 1, 5, 10 중 하나여야 합니다")
        self._speed = value
        logger.info(f"시뮬레이션 속도 변경: {value}x")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def event_bus(self):
        """기존 API 호환용 — 동기 이벤트 버스 반환"""
        return self._sync_event_bus

    def _effective_interval(self, base_seconds: float) -> float:
        """속도 배율을 적용한 실제 대기 시간 (초)"""
        return base_seconds / self._speed

    async def _publish_async(self, topic: str, data: dict):
        """비동기 이벤트 버스에 이벤트 발행 (있으면)"""
        if self.async_event_bus:
            await self.async_event_bus.publish(topic, data)

    async def _order_loop(self):
        """주문 자동 생성 루프"""
        logger.info("주문 생성 루프 시작")
        while self._running:
            try:
                interval = self._effective_interval(settings.ORDER_INTERVAL_SECONDS)
                await asyncio.sleep(interval)
                if self._running:
                    loop = asyncio.get_event_loop()
                    order = await loop.run_in_executor(
                        None, self.order_simulator.generate_order
                    )
                    # 비동기 이벤트 버스에도 발행
                    if order:
                        await self._publish_async("orders.created", {
                            "order_code": order.order_code,
                            "order_id": order.id,
                            "customer_id": order.customer_id,
                            "warehouse_id": order.warehouse_id,
                            "priority_score": order.priority_score,
                            "total_weight_kg": order.total_weight_kg,
                        })
                        # WebSocket 브로드캐스트
                        from app.api.websocket import broadcast_event
                        await broadcast_event("new_order", {
                            "order_code": order.order_code,
                            "priority_score": order.priority_score,
                            "total_weight_kg": order.total_weight_kg,
                        })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"주문 생성 루프 에러: {e}")
                await asyncio.sleep(5)

    async def _vehicle_loop(self):
        """차량 위치 업데이트 루프"""
        logger.info("차량 위치 업데이트 루프 시작")
        while self._running:
            try:
                interval = self._effective_interval(settings.VEHICLE_UPDATE_INTERVAL_SECONDS)
                await asyncio.sleep(interval)
                if self._running:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: self.vehicle_simulator.update_vehicles(interval_sec=30.0),
                    )
                    # 차량 상태 이벤트를 비동기 버스에도 발행
                    await self._publish_async("vehicles.updated", {
                        "update_type": "periodic",
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"차량 업데이트 루프 에러: {e}")
                await asyncio.sleep(5)

    async def start(self):
        """시뮬레이션 시작"""
        if self._running:
            logger.warning("시뮬레이션이 이미 실행 중입니다")
            return

        self._running = True
        self._tasks = [
            asyncio.create_task(self._order_loop()),
            asyncio.create_task(self._vehicle_loop()),
        ]
        logger.info(f"시뮬레이션 시작 (속도: {self._speed}x)")

    async def stop(self):
        """시뮬레이션 중지"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("시뮬레이션 중지")


# 싱글턴 인스턴스
simulation_manager = SimulationManager()
