"""
시뮬레이션 관련 Pydantic 스키마
"""

from typing import Literal
from pydantic import BaseModel


class TriggerAnomalyRequest(BaseModel):
    scenario: Literal[
        "ORDER_SURGE",
        "VEHICLE_BREAKDOWN",
        "STOCK_SHORTAGE",
        "SLA_RISK",
        "DOCK_CONGESTION",
    ]
    params: dict = {}  # 시나리오별 추가 파라미터


class TriggerAnomalyResponse(BaseModel):
    message: str
    scenario: str
    detail: dict = {}


class SpeedRequest(BaseModel):
    speed: Literal[1, 5, 10]


class SpeedResponse(BaseModel):
    message: str
    speed: int
