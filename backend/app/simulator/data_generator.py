"""
데이터 생성 유틸리티 — 시뮬레이터에서 공통으로 사용하는 헬퍼
"""

from datetime import datetime, timezone


def generate_order_code() -> str:
    """주문 코드 생성: ORD-YYYYMMDD-NNNNN"""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    # 밀리초 기반 시퀀스 — 충돌 가능성 낮음
    seq = int(now.timestamp() * 1000) % 100000
    return f"ORD-{date_str}-{seq:05d}"


def generate_shipment_code() -> str:
    """출하 코드 생성: SHP-YYYYMMDD-NNNNN"""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    seq = int(now.timestamp() * 1000) % 100000
    return f"SHP-{date_str}-{seq:05d}"


class DataGenerator:
    """시뮬레이터용 데이터 생성기"""

    @staticmethod
    def order_code() -> str:
        return generate_order_code()

    @staticmethod
    def shipment_code() -> str:
        return generate_shipment_code()
