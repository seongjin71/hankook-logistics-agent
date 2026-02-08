"""
주문 API — 주문 목록 조회, 우선순위 이력 조회
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.database import get_db
from app.models import Order, Customer, Warehouse, Product, PriorityHistory
from app.models.order import OrderItem, OrderStatus
from app.schemas.orders import (
    OrderResponse, OrderItemResponse, OrderListResponse, PriorityHistoryResponse,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _build_order_response(order: Order, db: Session) -> OrderResponse:
    """Order ORM → OrderResponse 변환 헬퍼"""
    customer = db.query(Customer).get(order.customer_id)
    warehouse = db.query(Warehouse).get(order.warehouse_id)

    items_resp = []
    for item in order.items:
        product = db.query(Product).get(item.product_id)
        items_resp.append(OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            sku_code=product.sku_code if product else None,
            product_name=product.name if product else None,
            quantity=item.quantity,
            weight_kg=item.weight_kg,
        ))

    return OrderResponse(
        id=order.id,
        order_code=order.order_code,
        customer_id=order.customer_id,
        customer_name=customer.name if customer else None,
        customer_grade=customer.grade.value if customer else None,
        warehouse_id=order.warehouse_id,
        warehouse_name=warehouse.name if warehouse else None,
        status=order.status.value if hasattr(order.status, 'value') else str(order.status),
        priority_score=order.priority_score,
        original_priority=order.original_priority,
        total_weight_kg=order.total_weight_kg,
        requested_delivery_at=order.requested_delivery_at,
        estimated_delivery_at=order.estimated_delivery_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items_resp,
    )


@router.get("", response_model=OrderListResponse)
def list_orders(
    status: str | None = Query(None, description="주문 상태 필터"),
    min_priority: float | None = Query(None, description="최소 우선순위 점수"),
    sort_by: str = Query("priority_score", description="정렬 기준 (priority_score, created_at)"),
    sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """주문 목록 조회"""
    query = db.query(Order)

    # 상태 필터
    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.filter(Order.status == status_enum)
        except ValueError:
            pass  # 잘못된 상태값은 무시

    # 최소 우선순위 필터
    if min_priority is not None:
        query = query.filter(Order.priority_score >= min_priority)

    # 전체 건수
    total = query.count()

    # 정렬
    sort_column = getattr(Order, sort_by, Order.priority_score)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # 페이지네이션
    orders = query.offset(offset).limit(limit).all()

    return OrderListResponse(
        total=total,
        orders=[_build_order_response(o, db) for o in orders],
    )


@router.get("/{order_id}/priority-history", response_model=list[PriorityHistoryResponse])
def get_priority_history(order_id: int, db: Session = Depends(get_db)):
    """주문의 우선순위 변경 이력 조회"""
    histories = (
        db.query(PriorityHistory)
        .filter(PriorityHistory.order_id == order_id)
        .order_by(desc(PriorityHistory.created_at))
        .all()
    )
    return [PriorityHistoryResponse.model_validate(h) for h in histories]
