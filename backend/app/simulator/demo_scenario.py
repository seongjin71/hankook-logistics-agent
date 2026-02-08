"""
15분 데모 시나리오 자동 실행.
시뮬레이션 속도 5x 기준으로 실제 ~3분에 완료되도록 타이밍 조절.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum

from app.simulator.simulation_manager import simulation_manager

logger = logging.getLogger(__name__)


class DemoPhase(str, Enum):
    NORMAL = "NORMAL_OPERATION"
    ORDER_SURGE = "ORDER_SURGE"
    VEHICLE_BREAKDOWN = "VEHICLE_BREAKDOWN"
    SLA_RISK = "SLA_RISK"
    RECOVERY = "RECOVERY"


PHASE_INFO = {
    DemoPhase.NORMAL: {"name": "Normal Operation", "index": 0},
    DemoPhase.ORDER_SURGE: {"name": "Order Surge", "index": 1},
    DemoPhase.VEHICLE_BREAKDOWN: {"name": "Vehicle Breakdown", "index": 2},
    DemoPhase.SLA_RISK: {"name": "SLA Risk", "index": 3},
    DemoPhase.RECOVERY: {"name": "Recovery", "index": 4},
}


class DemoScenario:
    """15분 데모 시나리오 자동 실행"""

    def __init__(self):
        self.demo_id: str | None = None
        self.is_running = False
        self.current_phase: DemoPhase | None = None
        self.phase_start: float = 0
        self.phase_duration: float = 0
        self.total_elapsed: float = 0
        self.total_duration: float = 210  # ~3.5min at 1x speed
        self.started_at: datetime | None = None
        self._task: asyncio.Task | None = None

    @property
    def status(self) -> dict:
        if not self.is_running:
            return {
                "demo_id": self.demo_id,
                "status": "stopped",
                "current_phase": None,
                "phase_name": None,
                "phase_index": None,
                "total_phases": 5,
                "elapsed_seconds": 0,
                "total_seconds": self.total_duration,
            }

        now = time.monotonic()
        phase_elapsed = now - self.phase_start if self.phase_start else 0

        return {
            "demo_id": self.demo_id,
            "status": "running",
            "current_phase": self.current_phase.value if self.current_phase else None,
            "phase_name": PHASE_INFO[self.current_phase]["name"] if self.current_phase else None,
            "phase_index": PHASE_INFO[self.current_phase]["index"] if self.current_phase else None,
            "total_phases": 5,
            "phase_elapsed": round(phase_elapsed, 1),
            "phase_duration": round(self.phase_duration, 1),
            "elapsed_seconds": round(
                (datetime.now(timezone.utc) - self.started_at).total_seconds()
                if self.started_at else 0, 1
            ),
            "total_seconds": self.total_duration,
        }

    async def start(self):
        if self.is_running:
            return {"error": "Demo is already running"}

        self.demo_id = str(uuid.uuid4())[:8]
        self.is_running = True
        self.started_at = datetime.now(timezone.utc)

        self._task = asyncio.create_task(self._run())
        logger.info(f"[Demo] 시나리오 시작: {self.demo_id}")

        return {
            "demo_id": self.demo_id,
            "status": "running",
            "phases": [
                {"phase": p.value, "name": PHASE_INFO[p]["name"]}
                for p in DemoPhase
            ],
        }

    async def stop(self):
        if not self.is_running:
            return {"status": "not_running"}

        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info(f"[Demo] 시나리오 중지: {self.demo_id}")
        return {"demo_id": self.demo_id, "status": "stopped"}

    async def _run(self):
        try:
            # Set speed to 5x for demo
            simulation_manager.speed = 5

            # Phase 0: Normal operation
            await self._phase_normal(30)

            # Phase 1: Order Surge
            await self._phase_order_surge(60)

            # Phase 2: Vehicle Breakdown (compound anomaly)
            await self._phase_vehicle_breakdown(60)

            # Phase 3: SLA Risk
            await self._phase_sla_risk(45)

            # Phase 4: Recovery
            await self._phase_recovery(15)

            logger.info(f"[Demo] 시나리오 완료: {self.demo_id}")

        except asyncio.CancelledError:
            logger.info(f"[Demo] 시나리오 취소됨: {self.demo_id}")
        except Exception as e:
            logger.error(f"[Demo] 시나리오 에러: {e}")
        finally:
            self.is_running = False
            self.current_phase = None

    async def _set_phase(self, phase: DemoPhase, duration: float):
        self.current_phase = phase
        self.phase_duration = duration
        self.phase_start = time.monotonic()
        logger.info(f"[Demo] Phase: {PHASE_INFO[phase]['name']} ({duration}s)")

        # Broadcast phase change via WebSocket
        from app.api.websocket import broadcast_event
        await broadcast_event("demo_phase", {
            "phase": phase.value,
            "phase_name": PHASE_INFO[phase]["name"],
            "phase_index": PHASE_INFO[phase]["index"],
            "duration": duration,
        })

    async def _wait(self, seconds: float):
        """Wait while checking if demo should stop"""
        end = time.monotonic() + seconds
        while time.monotonic() < end and self.is_running:
            await asyncio.sleep(0.5)
            if not self.is_running:
                raise asyncio.CancelledError()

    async def _phase_normal(self, duration: float):
        await self._set_phase(DemoPhase.NORMAL, duration)
        await self._wait(duration)

    async def _phase_order_surge(self, duration: float):
        await self._set_phase(DemoPhase.ORDER_SURGE, duration)

        # Trigger ORDER_SURGE
        anomaly_injector = simulation_manager.anomaly_injector
        anomaly_injector.inject_scenario("ORDER_SURGE")

        # Publish event to async bus for OODA pipeline
        if simulation_manager.async_event_bus:
            await simulation_manager.async_event_bus.publish("order.surge", {
                "type": "ORDER_SURGE",
                "source": "demo_scenario",
            })

        await self._wait(duration)

    async def _phase_vehicle_breakdown(self, duration: float):
        await self._set_phase(DemoPhase.VEHICLE_BREAKDOWN, duration)

        # Trigger VEHICLE_BREAKDOWN
        anomaly_injector = simulation_manager.anomaly_injector
        anomaly_injector.inject_scenario("VEHICLE_BREAKDOWN")

        if simulation_manager.async_event_bus:
            await simulation_manager.async_event_bus.publish("vehicle.breakdown", {
                "type": "VEHICLE_BREAKDOWN",
                "source": "demo_scenario",
            })

        await self._wait(duration)

    async def _phase_sla_risk(self, duration: float):
        await self._set_phase(DemoPhase.SLA_RISK, duration)

        # Trigger SLA_RISK
        anomaly_injector = simulation_manager.anomaly_injector
        anomaly_injector.inject_scenario("SLA_RISK")

        if simulation_manager.async_event_bus:
            await simulation_manager.async_event_bus.publish("sla.risk", {
                "type": "SLA_RISK",
                "source": "demo_scenario",
            })

        await self._wait(duration)

    async def _phase_recovery(self, duration: float):
        await self._set_phase(DemoPhase.RECOVERY, duration)

        # Slow down to normal speed
        simulation_manager.speed = 1

        await self._wait(duration)


# Singleton
demo_scenario = DemoScenario()
