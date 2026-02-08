"""
이벤트 버스 — Redis Stream 기반, Redis 없으면 인메모리 큐로 fallback
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class InMemoryEventBus:
    """Redis 없을 때 사용하는 인메모리 이벤트 버스"""

    def __init__(self):
        self._streams: dict[str, list[dict]] = defaultdict(list)
        self._max_size = 1000  # 스트림당 최대 이벤트 수

    def publish(self, stream: str, data: dict):
        """이벤트를 스트림에 발행"""
        event = {
            "id": f"{len(self._streams[stream]) + 1}",
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._streams[stream].append(event)
        # 최대 크기 초과 시 오래된 이벤트 제거
        if len(self._streams[stream]) > self._max_size:
            self._streams[stream] = self._streams[stream][-self._max_size:]

    def get_recent(self, stream: str, count: int = 10) -> list[dict]:
        """최근 이벤트 조회"""
        return self._streams[stream][-count:]

    def get_all_streams(self) -> dict[str, int]:
        """모든 스트림의 이벤트 수 반환"""
        return {k: len(v) for k, v in self._streams.items()}


class EventBus:
    """
    Redis Stream 래퍼 — Redis 연결 실패 시 InMemoryEventBus로 fallback
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis = None
        self._in_memory = InMemoryEventBus()
        self._use_redis = False

        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            self._use_redis = True
            logger.info("Redis 연결 성공 — Redis Stream 사용")
        except Exception:
            logger.warning("Redis 연결 실패 — 인메모리 이벤트 버스로 fallback")

    @property
    def is_redis(self) -> bool:
        return self._use_redis

    def publish(self, stream: str, data: dict):
        """이벤트 발행"""
        if self._use_redis:
            try:
                # Redis Stream에 추가
                serialized = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                              for k, v in data.items()}
                self._redis.xadd(stream, serialized, maxlen=1000)
            except Exception as e:
                logger.error(f"Redis publish 실패: {e}, 인메모리로 fallback")
                self._in_memory.publish(stream, data)
        else:
            self._in_memory.publish(stream, data)

    def get_recent(self, stream: str, count: int = 10) -> list[dict]:
        """최근 이벤트 조회"""
        if self._use_redis:
            try:
                entries = self._redis.xrevrange(stream, count=count)
                return [{"id": eid, "data": edata} for eid, edata in entries]
            except Exception:
                return self._in_memory.get_recent(stream, count)
        return self._in_memory.get_recent(stream, count)
