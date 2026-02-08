"""
SQLAlchemy ORM 모델 패키지
- 모든 모델을 여기서 import하여 Base.metadata에 등록한다.
"""

from app.models.product import Product
from app.models.customer import Customer
from app.models.warehouse import Warehouse
from app.models.vehicle import Vehicle
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.shipment import Shipment
from app.models.agent_event import AgentEvent
from app.models.priority_history import PriorityHistory

__all__ = [
    "Product",
    "Customer",
    "Warehouse",
    "Vehicle",
    "Inventory",
    "Order",
    "OrderItem",
    "Shipment",
    "AgentEvent",
    "PriorityHistory",
]
