"""
FastAPI 앱 엔트리포인트
- CORS 설정
- 라우터 등록 (WebSocket, Actions 포함)
- AsyncEventBus + Monitor Agent + OODA Orchestrator + 시뮬레이터 백그라운드 시작
- 헬스체크 엔드포인트
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api import dashboard, orders, simulation, agents
from app.api.websocket import router as ws_router
from app.api.actions import router as actions_router, set_action_agent
from app.schemas.common import HealthResponse
from app.events.event_bus import AsyncEventBus
from app.agents.monitor_agent import MonitorAgent
from app.agents.orchestrator import OODAOrchestrator
from app.simulator.simulation_manager import simulation_manager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 모듈 수준 참조 (lifespan 내에서 생성되어 shutdown에서 정리)
_async_event_bus: AsyncEventBus | None = None
_monitor_agent: MonitorAgent | None = None
_orchestrator: OODAOrchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 전체 백그라운드 컴포넌트 관리"""
    global _async_event_bus, _monitor_agent, _orchestrator

    # ── 1. DB 테이블 확인 ──
    Base.metadata.create_all(bind=engine)
    logger.info("데이터베이스 테이블 확인 완료")

    # 마스터 데이터 존재 여부 확인
    db = SessionLocal()
    try:
        from app.models import Product
        product_count = db.query(Product).count()
        if product_count == 0:
            logger.warning("마스터 데이터가 없습니다. 먼저 python seed_data.py를 실행하세요.")
        else:
            logger.info(f"마스터 데이터 확인: Products {product_count}개")
    finally:
        db.close()

    # ── 2. AsyncEventBus 생성 ──
    _async_event_bus = AsyncEventBus(settings.REDIS_URL)

    # ── 3. Monitor Agent 생성 및 이벤트 구독 등록 ──
    _monitor_agent = MonitorAgent(_async_event_bus)
    await _monitor_agent.start()
    logger.info("Monitor Agent 시작 완료")

    # ── 4. OODA Orchestrator 생성 및 이벤트 구독 등록 ──
    _orchestrator = OODAOrchestrator(_async_event_bus)
    await _orchestrator.start()
    # Action Agent를 actions API에 연결
    set_action_agent(_orchestrator.action_agent)
    logger.info("OODA Orchestrator 시작 완료 (Anomaly → Priority → Action)")

    # ── 5. AsyncEventBus 시작 (구독자 루프) ──
    await _async_event_bus.start()
    logger.info("AsyncEventBus 시작 완료")

    # ── 6. 시뮬레이터에 AsyncEventBus 연결 및 시작 ──
    simulation_manager.set_async_event_bus(_async_event_bus)
    await simulation_manager.start()
    logger.info("시뮬레이션 백그라운드 태스크 시작")

    yield

    # ── 종료 ──
    await simulation_manager.stop()
    logger.info("시뮬레이션 중지 완료")

    if _monitor_agent:
        await _monitor_agent.stop()
        logger.info("Monitor Agent 중지 완료")

    if _async_event_bus:
        await _async_event_bus.stop()
        logger.info("AsyncEventBus 중지 완료")


app = FastAPI(
    title="한국타이어 출하물류 AI 에이전트 시스템",
    description="실시간 출하 물류 우선순위 결정 및 실행 데모",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS 설정 — 모든 오리진 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(dashboard.router)
app.include_router(orders.router)
app.include_router(simulation.router)
app.include_router(agents.router)
app.include_router(actions_router)
app.include_router(ws_router)


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    """시스템 상태 확인"""
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db_ok = True
        db.close()
    except Exception:
        pass

    redis_ok = _async_event_bus.is_redis if _async_event_bus else False

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        db_connected=db_ok,
        redis_connected=redis_ok,
        simulation_running=simulation_manager.is_running,
        timestamp=datetime.now(timezone.utc),
    )


# ── Static file serving (unified Docker deployment) ──
_static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(_static_dir):
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(_static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_static_dir, "index.html"))
