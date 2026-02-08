"""
차량 시뮬레이터 — IN_TRANSIT 차량의 위치/연료를 주기적으로 업데이트한다.
"""

import math
import random
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Vehicle, Warehouse
from app.models.vehicle import VehicleStatus
from app.simulator.event_bus import EventBus

logger = logging.getLogger(__name__)

# 주요 도시 좌표 (배송 목적지 후보)
DESTINATIONS = [
    (37.5665, 126.9780),  # 서울
    (35.1796, 129.0756),  # 부산
    (35.8714, 128.6014),  # 대구
    (37.4563, 126.7052),  # 인천
    (35.1595, 126.8526),  # 광주
    (36.3504, 127.3845),  # 대전
    (35.5384, 129.3114),  # 울산
    (37.2636, 127.0286),  # 수원
    (37.3943, 127.1110),  # 성남
    (35.2270, 128.6811),  # 창원
]


class VehicleSimulator:
    """차량 위치/상태 시뮬레이터"""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        # 차량별 목적지 저장 (vehicle_id → (lat, lng))
        self._destinations: dict[int, tuple[float, float]] = {}

    def _assign_destination(self, vehicle: Vehicle):
        """운행 중 차량에 랜덤 목적지 배정"""
        if vehicle.id not in self._destinations:
            self._destinations[vehicle.id] = random.choice(DESTINATIONS)

    def _move_toward(self, current_lat: float, current_lng: float,
                     dest_lat: float, dest_lng: float,
                     speed_kmh: float, interval_sec: float) -> tuple[float, float]:
        """현재 위치에서 목적지 방향으로 이동한 새 좌표 반환"""
        # 거리 계산 (간이 — 직선거리, km)
        dlat = dest_lat - current_lat
        dlng = dest_lng - current_lng
        dist_deg = math.sqrt(dlat ** 2 + dlng ** 2)

        if dist_deg < 0.01:  # 목적지 도달
            return dest_lat, dest_lng

        # 이동 거리 (위도 1도 ≈ 111km)
        move_km = speed_kmh * (interval_sec / 3600)
        move_deg = move_km / 111.0

        # 방향 벡터 정규화 후 이동
        ratio = min(move_deg / dist_deg, 1.0)
        new_lat = current_lat + dlat * ratio
        new_lng = current_lng + dlng * ratio

        return round(new_lat, 6), round(new_lng, 6)

    def update_vehicles(self, db: Session | None = None, interval_sec: float = 30.0):
        """
        IN_TRANSIT 상태 차량의 위치와 연료를 업데이트한다.
        interval_sec: 이 업데이트가 시뮬레이션 상에서 몇 초에 해당하는지
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()

        try:
            vehicles = db.query(Vehicle).filter(
                Vehicle.status == VehicleStatus.IN_TRANSIT
            ).all()

            for vehicle in vehicles:
                self._assign_destination(vehicle)
                dest_lat, dest_lng = self._destinations[vehicle.id]

                # 속도가 0이면 랜덤 속도 부여
                if vehicle.current_speed_kmh <= 0:
                    vehicle.current_speed_kmh = random.uniform(40, 80)

                # 위치 이동
                if vehicle.current_lat is not None and vehicle.current_lng is not None:
                    new_lat, new_lng = self._move_toward(
                        vehicle.current_lat, vehicle.current_lng,
                        dest_lat, dest_lng,
                        vehicle.current_speed_kmh, interval_sec,
                    )
                    vehicle.current_lat = new_lat
                    vehicle.current_lng = new_lng

                    # 목적지 도달 확인
                    if abs(new_lat - dest_lat) < 0.01 and abs(new_lng - dest_lng) < 0.01:
                        vehicle.status = VehicleStatus.AVAILABLE
                        vehicle.current_speed_kmh = 0
                        # 원래 창고로 위치 복귀
                        if vehicle.warehouse_id:
                            wh = db.query(Warehouse).get(vehicle.warehouse_id)
                            if wh:
                                vehicle.current_lat = wh.location_lat
                                vehicle.current_lng = wh.location_lng
                        del self._destinations[vehicle.id]
                        logger.info(f"차량 {vehicle.vehicle_code} 배송 완료 → AVAILABLE")

                # 연료 감소 (주행 시 100km당 약 5% 소모)
                fuel_consumed = (vehicle.current_speed_kmh * interval_sec / 3600) / 100 * 5
                vehicle.fuel_level_pct = max(0, vehicle.fuel_level_pct - fuel_consumed)

                vehicle.updated_at = datetime.now(timezone.utc)

                # 이벤트 발행
                self.event_bus.publish("vehicles.updated", {
                    "vehicle_code": vehicle.vehicle_code,
                    "status": vehicle.status.value,
                    "lat": vehicle.current_lat,
                    "lng": vehicle.current_lng,
                    "speed_kmh": vehicle.current_speed_kmh,
                    "fuel_pct": round(vehicle.fuel_level_pct, 1),
                })

            db.commit()

            if vehicles:
                logger.debug(f"차량 위치 업데이트: {len(vehicles)}대")

        except Exception as e:
            if own_session:
                db.rollback()
            logger.error(f"차량 업데이트 실패: {e}")
            raise
        finally:
            if own_session:
                db.close()
