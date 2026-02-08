"""
주문 관련 Pydantic 스키마
"""

from datetime import datetime
from pydantic import BaseModel


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    sku_code: str | None = None
    product_name: str | None = None
    quantity: int
    weight_kg: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    order_code: str
    customer_id: int
    customer_name: str | None = None
    customer_grade: str | None = None
    warehouse_id: int
    warehouse_name: str | None = None
    status: str
    priority_score: float
    original_priority: float
    total_weight_kg: float
    requested_delivery_at: datetime
    estimated_delivery_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    total: int
    orders: list[OrderResponse]


class PriorityHistoryResponse(BaseModel):
    id: int
    order_id: int
    previous_score: float
    new_score: float
    reason: str
    agent_event_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
