"""
애플리케이션 설정
- SQLite DB, Redis, 시뮬레이션 관련 설정을 관리한다.
"""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 데이터베이스
    DATABASE_URL: str = "sqlite:///logistics.db"

    # Redis (없으면 인메모리 큐로 fallback)
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # 시뮬레이션 기본 속도 (1x, 5x, 10x)
    SIMULATION_DEFAULT_SPEED: int = 1

    # 기본 주문 생성 간격 (초) — 1x 기준
    ORDER_INTERVAL_SECONDS: float = 90.0

    # 차량 위치 업데이트 간격 (초) — 1x 기준
    VEHICLE_UPDATE_INTERVAL_SECONDS: float = 30.0

    # Claude API
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-sonnet-4-5-20250929"
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
