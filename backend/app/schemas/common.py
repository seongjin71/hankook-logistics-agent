"""
공통 Pydantic 스키마
"""

from datetime import datetime
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    redis_connected: bool
    simulation_running: bool
    timestamp: datetime


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
